# tenant_router.py
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Body, Path, status, Response

import services.authService as auth_service
import services.attService as attachment_service
from services.logService import setup_logger

from datetime import datetime

logger = setup_logger(__name__)
router = APIRouter(prefix="/tenant", tags=["Tenant Management"])


class TenantCredentials(BaseModel):
    """Schema for tenant credentials used in init and update operations."""

    tenant_id: str = Field(..., example="your-tenant-id")
    client_id: str = Field(..., example="your-client-id")
    client_secret: str = Field(..., example="your-client-secret")


class SuccessResponse(BaseModel):
    """Generic success response schema."""

    status: str = "success"
    message: str
    data: dict | None = None


# change start
import services.m365Connector as m365API
from services.tenantService import TenantService
from services.dataService import DataService
import services.mailService as mail_service
from common.constants import Collection
from common.cipher import UUIDBase62Cipher

data_service = DataService().get_data_service()


async def get_graph_client(tenant_id):
    tenant_service = TenantService(tenant_id)
    client_ID = tenant_service.getTenantAppId()
    client_secret = tenant_service.getTenantAppSecret()
    graph_clinet = await auth_service.get_graph_client(
        tenant_id, client_ID, client_secret
    )
    return graph_clinet


async def sync_data_cron():
    db_names = data_service.client.list_database_names()
    tenants = [database for database in db_names if database not in ["admin", "config", "local"]]
    for tenant in tenants:
        tenant_id = UUIDBase62Cipher.decode(tenant)
        graph_client = await get_graph_client(tenant_id)
        latest_mail = await mail_service.getLatestMail(graph_client, tenant_id)
    logger.info(f"Task is running at {datetime.now()}")


async def get_user_list_API(tenant_id):
    tenant_service = TenantService(tenant_id)
    hash_tid = tenant_service.getTenantHashed()
    collection_user = Collection.USER
    query = {}
    user_list = data_service.read(hash_tid, collection_user, query)
    logger.info(user_list)
    return user_list


async def get_user_mails_API(tenant_id, user_id):
    graph_client = await get_graph_client(tenant_id)
    tenant_service = TenantService(tenant_id)
    hash_tid = tenant_service.getTenantHashed()
    collection_mail = Collection.MAIL
    query = {"user_id": user_id}
    mails = data_service.read(hash_tid, collection_mail, query)
    return mails


async def get_all_users(tenant_id):
    user_list = await get_user_list_API(tenant_id)
    return user_list


async def get_specific_user(tenant_id, user_id):
    user_list = await get_user_list_API(tenant_id)
    for user in user_list:
        if user.get("id") == user_id:
            return user
    return None


async def get_user_all_mail(tenant_id, user_id):
    user_mails = await get_user_mails_API(tenant_id, user_id)
    return user_mails


async def get_specific_mail(tenant_id, user_id, message_id):
    user_mails = await get_user_mails_API(tenant_id, user_id)
    for mail in user_mails:
        if mail.get("message_id") == message_id:
            return mail
    return None

async def get_specific_eml(tenant_id, user_id, message_id):
    user_mails = await get_user_mails_API(tenant_id, user_id)
    for mail in user_mails:
        if mail.get("message_id") == message_id:
            tenant_service = TenantService(tenant_id)
            hash_tid = tenant_service.getTenantHashed()
            fs = data_service.get_gridfs(hash_tid)
            cursor = fs.find({"filename": f"{message_id}.eml"})
            for eml in cursor:
                content = eml.read()
                from fastapi.responses import Response
                return Response(content, media_type="message/rfc822")
    return None
# change end


@router.post("/init", response_model=SuccessResponse)
async def init_tenant(credentials: TenantCredentials = Body(...)):
    """Initializes a new tenant, fetches all user and mail data, and saves it."""
    try:
        await auth_service.auth_init_tenant(
            credentials.tenant_id, credentials.client_id, credentials.client_secret
        )
        return SuccessResponse(
            message=f"Tenant {credentials.tenant_id} initialized successfully."
        )
    except auth_service.AlreadyInitializedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except auth_service.GraphAPIError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except auth_service.TenantInitializationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error occurred in init_tenant: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/update", response_model=SuccessResponse)
async def update_tenant(credentials: TenantCredentials = Body(...)):
    """Updates the credentials for an existing tenant."""
    try:
        await auth_service.auth_update_tenant(
            credentials.tenant_id, credentials.client_id, credentials.client_secret
        )
        return SuccessResponse(message="Tenant credentials updated successfully.")
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except auth_service.GraphAPIError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except auth_service.TenantUpdateError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error occurred in update: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/mails")
async def get_mails(tenant_id: str = Path(..., description="The ID of the tenant")):
    """Retrieves the list of all users for a given tenant from local storage."""
    try:
        graph_client = await get_graph_client(tenant_id)
        mails = await mail_service.getMail(graph_client, tenant_id)
        return mails
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_mails: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users")
async def get_users(tenant_id: str = Path(..., description="The ID of the tenant")):
    """Retrieves the list of all users for a given tenant from local storage."""
    try:
        users = await get_all_users(tenant_id)
        return users
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_users: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}")
async def get_user(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user to retrieve"),
):
    """Retrieves data for a single, specific user from local storage."""
    try:
        user = await get_specific_user(tenant_id, user_id)
        return user
    except (auth_service.TenantNotFoundError, auth_service.UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_user: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}/mails")
async def get_user_mails(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
):
    """Retrieves all emails for a specific user from local storage."""
    try:
        mails = await get_user_all_mail(tenant_id, user_id)
        return mails
    except (auth_service.TenantNotFoundError, auth_service.UserNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_user_mails: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}/mails/{message_id}")
async def get_mail(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message to retrieve"),
):
    """Retrieves data for a single, specific email from local storage."""
    try:
        mail = await get_specific_mail(tenant_id, user_id, message_id)
        return mail
    except (auth_service.TenantNotFoundError, auth_service.MailNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_mail: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}/mails/{message_id}/eml")
async def get_mail(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message to retrieve"),
):
    """Retrieves data for a single, specific email from local storage."""
    try:
        mail = await get_specific_eml(tenant_id, user_id, message_id)
        return mail
    except (auth_service.TenantNotFoundError, auth_service.MailNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in get_mail: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{tenant_id}/users/{user_id}/mails/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_mail(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message to delete"),
):
    """Deletes a specific email for a user."""
    try:
        # await delete_user_mail(tenant_id, user_id, message_id)
        graph_client = await get_graph_client(tenant_id)
        await mail_service.delMail(graph_client, tenant_id, user_id, message_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except auth_service.GraphAPIError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in delete_mail: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{tenant_id}/users/{user_id}/mails/{message_id}/attachments")
async def get_attachments_list(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message"),
):
    """Retrieves a list of all attachments for a specific email via Graph API."""
    try:
        attachments = await attachment_service.get_all_attachments(
            tenant_id, user_id=user_id, message_id=message_id
        )
        return attachments
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except auth_service.GraphAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not retrieve attachments. Verify message ID and permissions. Error: {e}",
        )
    except Exception as e:
        logger.error(f"Error occurred in get_attachments_list: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{tenant_id}/users/{user_id}/mails/{message_id}/attachments/{attachment_id}"
)
async def get_attachment(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message"),
    attachment_id: str = Path(..., description="The ID of the attachment to retrieve"),
):
    """Retrieves a single attachment's details, including its content (Base64 encoded), via Graph API."""
    try:
        attachment = await attachment_service.get_attachment(
            tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_id=attachment_id,
        )
        return attachment
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except auth_service.GraphAPIError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error occurred in get_attachment: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{tenant_id}/users/{user_id}/mails/{message_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_attachment(
    tenant_id: str = Path(..., description="The ID of the tenant"),
    user_id: str = Path(..., description="The ID of the user (GUID)"),
    message_id: str = Path(..., description="The ID of the email message"),
    attachment_id: str = Path(..., description="The ID of the attachment to delete"),
):
    """Deletes a specific attachment from an email."""
    try:
        graph_client = await get_graph_client(tenant_id)
        await attachment_service.delete_attachment(
            graph_client,
            tenant_id,
            user_id=user_id,
            message_id=message_id,
            attachment_id=attachment_id,
            request_to_m365=True,
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except auth_service.TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except auth_service.GraphAPIError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error occurred in delete_attachment: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/test/delete_database/{tenant_id}")
async def delete_database(tenant_id: str):
    """test for delete database"""
    from services.tenantService import TenantService

    tenant_service = TenantService(tenant_id)
    tenant_service.delete()
    return {"ok": True}
