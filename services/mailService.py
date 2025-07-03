from typing import Optional
from azure.core.exceptions import ClientAuthenticationError
from msgraph import GraphServiceClient

from datetime import datetime, timezone
import inspect

from services.dataService import DataService
from services.m365Connector import getEMLByMessageId, getTenantUserList, deleteMail, getTenantMailChangeSet, getUserMails
from common.constants import Collection, LogLevel
from services.tenantService import TenantService
from logger.operationLogger import OperationLogger
from services.attService import create_attachment, delete_attachment

logger = OperationLogger()
data_service = DataService().get_data_service()

async def getMail(client, tenant_id: str):
    logger.log(LogLevel.INFO, "getMail", "try to getMail", tenant_id=tenant_id)
    if not client:
        msg = "Graph client is required"
        logger.log(LogLevel.ERROR, "getMail", msg)
        return _response_error(msg)

    if not tenant_id:
        msg = "Tenant ID is required"
        logger.log(LogLevel.ERROR, "getMail", msg)
        return _response_error(msg)

    tenant_service = TenantService(tenant_id)
    try:
        users = await getTenantUserList(client)
        if not users:
            msg = "No users found in tenant"
            logger.log(LogLevel.WARNING, "getMail", msg, tenant=tenant_id)
            return _response_success([])

        users_with_mails = []

        for user in users:
            user_id = user.get("id", "")
            logger.log(LogLevel.INFO, "getMail", f"Fetching mail for user {user_id}", tenant=tenant_id)

            try:
                infos = await getUserMails(client, user_id)
                delta_link = infos.get("deltalink", "")
                tenant_service.updateTenantUserDeltaLink(user_id, delta_link)

                mails = infos.get("mails", [])
                mail_docs = []
                for msg in mails:
                    mail_doc = await _process_mail(client, user_id, tenant_id, msg)
                    mail_docs.append({"mail": mail_doc})

                users_with_mails.append({
                    "user_id": user_id,
                    "mails": mail_docs
                })

            except Exception as ue:
                logger.log(LogLevel.ERROR, "getMail", f"Error fetching mail for user {user_id}", tenant=tenant_id, error=str(ue))
                continue  # Skip user on failure

        return _response_success(users_with_mails)

    except Exception as e:
        logger.log(LogLevel.ERROR, "getMail", "Unexpected error", tenant=tenant_id, error=str(e))
        return _response_error(str(e))

async def getLatestMail(client: GraphServiceClient, tenant_id):
    logger.log(LogLevel.INFO, "getLatestMail", "try to getLatestMail", tenant_id=tenant_id)
    try:
        tenant_service = TenantService(tenant_id)
        encrypted_db_name = tenant_service.getTenantHashed()
        users = await getTenantUserList(client)

        changes = []
        for user in users:
            user_id = user.get("id")
            if not user_id:
                continue
            delta_link = tenant_service.getTenantUseDeltaLink(user_id)
            change_result = await getTenantMailChangeSet(client, user_id, delta_link)
            if not change_result:
                continue

            delta_link = change_result.get("delta_link", "")
            tenant_service.updateTenantUserDeltaLink(user_id, delta_link)

            mail_docs = []
            for mail in change_result["mails"]:
                message_id = mail.get("id", "")

                if mail.get("@removed"):
                    logger.log(LogLevel.INFO, "getLatestMail", "Mail was deleted", user_id=user_id, message_id=message_id)
                    await delMail(client, tenant_id, user_id, message_id)
                    mail_docs.append({"state": "deleted", "data": message_id})
                else: # need Updated
                    try:
                        mail_doc = await _process_mail(client, user_id, tenant_id, mail)
                        mail_docs.append({"state": "changed", "data": mail_doc})
                    except Exception as e:
                        logger.log(LogLevel.ERROR, "getLatestMail", "Failed to fetch full mail content", message_id=message_id, error=str(e))
            if mail_docs:
                changes.append({
                    "user_id": user_id,
                    "mails": mail_docs
                })
        return _response_success(changes)

    except Exception as e:
        logger.log(LogLevel.ERROR, "getLatestMail", "Unexpected error", tenant=tenant_id, message_id=message_id, error=str(e))
        return _response_error(f"Unexpected error: {str(e)}")

async def delMail(client, tenant_id: str, user_id: str, message_id: str):
    logger.log(LogLevel.INFO, "DeleteMail", "Try to delete mail", tenant=tenant_id, user_id=user_id, message_id=message_id)
    tenant_service = TenantService(tenant_id)
    encrypted_db_name = tenant_service.getTenantHashed()

    try:
        # try to remove mail on m365 by api
        await deleteMail(client, user_id, message_id)

        # try to clear info stored on our system
        # 1. query does this mail exist in our system
        existing = data_service.read(encrypted_db_name, Collection.MAIL.value, {
            "user_id": user_id,
            "message_id": message_id
        })

        if not existing:
            logger.log(LogLevel.WARNING, "DeleteMail", "Message not found", tenant=tenant_id, message_id=message_id)
            return _response_error("Message not found")

        mail_doc = existing[0]
        # 2. remove eml
        if "eml_file_id" in mail_doc and mail_doc["eml_file_id"]:
            try:
                data_service.delete_eml(encrypted_db_name, mail_doc["eml_file_id"])
                logger.log(LogLevel.INFO, "DeleteMail", "Deleted EML from GridFS", message_id=message_id)
            except Exception as e:
                logger.log(LogLevel.ERROR, "DeleteMail", "Failed to delete EML", message_id=message_id, error=str(e))

        # 3. remove info stored in attachments collection
        await _process_att_collection(tenant_id, user_id, message_id, [])
        logger.log(LogLevel.INFO, "DeleteMail", "Deleted attachments", user_id=user_id, message_id=message_id)

        # 4. update metadata (soft delete)
        if not mail_doc.get("is_deleted", False):
            synced_at = _now_iso_time()
            change_entry = {
                "synced_at": synced_at,
                "change_type": "deleted"
            }

            update_doc = {
                "$set": {
                    "synced_at": synced_at,
                    "change_type": "deleted",
                    "is_deleted": True
                },
                "$push": {
                    "change_history": change_entry
                }
            }

            data_service.update_one(encrypted_db_name, Collection.MAIL.value, {
                "user_id": user_id,
                "message_id": message_id
            }, update_doc)
            logger.log(LogLevel.INFO, "DeleteMail", "Soft-deleted message metadata", message_id=message_id)
        return _response_success([])
    except Exception as e:
        logger.log(LogLevel.ERROR, "DeleteMail", "Unexpected error", tenant=tenant_id, message_id=message_id, error=str(e))
        return _response_error(f"Unexpected error: {str(e)}")


def _now_iso_time():
    return datetime.now().isoformat()

def _add_diff(old_data, new_data, keys):
    diff = {}
    for key in keys:
        old = old_data.get(key)
        new = new_data.get(key)
        if old != new:
            diff[key] = {"old": old, "new": new}
    return diff

def _response_success(data):
    return {
        "status": "success",
        "data": data
    }

def _response_error(message, code=500):
    return {
        "status": "error",
        "message": message,
        "code": code
    }

async def _process_mail(client, user_id, tenant_id, msg: dict):
    synced_at = _now_iso_time()
    message_id = msg["id"]
    subject = msg["subject"]
    attachments = msg["attachments"]
    has_attachments = bool(attachments)

    tenant_service = TenantService(tenant_id)
    encrypted_db_name = tenant_service.getTenantHashed()

    if has_attachments:
        attachments = sorted(attachments, key=lambda x: (x["id"], x["name"]))
        await _process_att_collection(tenant_id, user_id, message_id, attachments)

    # get eml
    try:
        eml_content = await getEMLByMessageId(client, user_id, message_id)
    except Exception as e:
        logger.log(LogLevel.ERROR, "EML", "Failed to get EML", user_id=user_id, message_id=message_id, error=str(e))
        eml_content = None

    eml_file_id = None
    if eml_content:
        eml_file_id = data_service.save_or_update_eml(encrypted_db_name, message_id, eml_content)

    # exist?
    existing = data_service.read(encrypted_db_name, Collection.MAIL.value, {
        "message_id": message_id,
        "user_id": user_id
    })

    if not existing:
        logger.log(LogLevel.INFO, "Metadata", "Creating new metadata record", message_id=message_id)
        msg_doc = {
            "message_id": message_id,
            "user_id": user_id,
            "subject": subject,
            "attachments": attachments,
            "synced_at": synced_at,
            "change_type": "created",
            "change_history": [
                {
                    "synced_at": synced_at,
                    "change_type": "created"
                }
            ],
            "eml_file_id": str(eml_file_id) if eml_file_id else "",
            "is_deleted": False
        }
        data_service.create_one(encrypted_db_name, Collection.MAIL.value, msg_doc)
    else:
        current = existing[0]
        diff = _add_diff(current, {
            "subject": subject,
            "attachments": attachments,
        }, keys=["subject", "attachments"])

        if not diff and not eml_file_id:
            logger.log(LogLevel.INFO, "Metadata", "No change detected", message_id=message_id)
        else:
            update_doc = {
                "$set": {
                    "subject": subject,
                    "attachments": attachments,
                    "synced_at": synced_at,
                    "change_type": "updated",
                    "is_deleted": False
                },
                "$push": {
                    "change_history": {
                        "synced_at": synced_at,
                        "change_type": "updated",
                        "diff": diff if diff else {}
                    }
                }
            }
            if eml_file_id:
                update_doc["$set"]["eml_file_id"] = str(eml_file_id)

            query = {
                "message_id": message_id,
                "user_id": user_id
            }

            logger.log(LogLevel.INFO, "Metadata", "Updated metadata with changes", message_id=message_id, changes=diff)
            data_service.update_one(encrypted_db_name, Collection.MAIL.value, query, update_doc)
    return {
            "message_id": message_id,
            "user_id": user_id,
            "subject": subject,
            "attachments": attachments,
            "content": eml_content if eml_content else ""
    }

async def _process_attachment_service_action(
    action: str,
    tenant_id: str,
    user_id: str,
    message_id: str,
    attachment_ids: set[str],
    handler: callable,
    request_to_m365: bool = False,
):
    if not attachment_ids:
        return True

    if inspect.iscoroutinefunction(handler):
        result = await handler(
            tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_id=list(attachment_ids),
            request_to_m365=request_to_m365,
        )
    else:
        result = handler(
            tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_id=list(attachment_ids),
        )

    if not result:
        logger.log(
            LogLevel.ERROR,
            f"{action}_attachment",
            f"Failed to {action} attachments for user {user_id}, message {message_id}, ids: {attachment_ids}, request_to_m365: {request_to_m365}."
        )

    return result

async def _process_att_collection(tenant_id, user_id, message_id, attachments):
    tenant_service = TenantService(tenant_id)
    encrypted_db_name = tenant_service.getTenantHashed()

    existing_att_docs = data_service.read(encrypted_db_name, Collection.ATT.value, {
        "message_id": message_id,
        "user_id": user_id
    })

    existing_att_ids = {doc["attachment_id"] for doc in existing_att_docs}
    current_att_ids = {att["id"] for att in attachments}
    # attachments needs to be added
    new_att_ids = current_att_ids - existing_att_ids
    if new_att_ids:
        await _process_attachment_service_action(
            action="create",
            tenant_id=tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_ids=new_att_ids,
            handler=create_attachment,
        )

    # attachments needs to be deleted
    removed_att_ids = existing_att_ids - current_att_ids
    if removed_att_ids:
        await _process_attachment_service_action(
            action="delete",
            tenant_id=tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_ids=removed_att_ids,
            handler=delete_attachment,
            request_to_m365=False,
        )
