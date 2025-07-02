# Danny

from typing import Optional
from common.constants import Collection
from msgraph import GraphServiceClient
from services.authService import get_graph_client
from services.m365Connector import deleteAtt
from services.dataService import MongoDataService
from services.logService import setup_logger
from services.tenantService import TenantService
from common.cipher import UUIDBase62Cipher

mongo = MongoDataService()
Success = bool

logger = setup_logger(__name__)


def create_attachment(
    tid: str, /, user_id: str, message_id: str, attachment_id: str | list[str]
) -> Success:
    is_attachment_array = hasattr(attachment_id, "__len__") and (
        not isinstance(attachment_id, str)
    )

    try:
        if is_attachment_array:
            data = [
                {"user_id": user_id, "message_id": message_id, "attachment_id": att_id}
                for att_id in attachment_id
            ]
            mongo.create_many(UUIDBase62Cipher.encode(tid), Collection.ATT, data)
        else:
            data = {
                "user_id": user_id,
                "message_id": message_id,
                "attachment_id": attachment_id,
            }
            mongo.create_one(UUIDBase62Cipher.encode(tid), Collection.ATT, data)
        return True
    except Exception as e:
        logger.error(f"Error occurred in create_attachment: {e}")
        return False


async def delete_attachment(
    tid: str,
    /,
    user_id: str,
    message_id: str,
    attachment_id: str,
    request_to_m365: Optional[bool] = True,
):
    try:
        tenant = TenantService(tid)

        client: GraphServiceClient = await get_graph_client(
            tid, tenant.getTenantAppId(), tenant.getTenantAppSecret()
        )

        if request_to_m365:
            await deleteAtt(client, user_id, message_id, attachment_id)

        mongo.delete_one(
            UUIDBase62Cipher.encode(tid),
            "attachments",
            {
                "user_id": user_id,
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
        )
        return True
    except Exception as e:
        logger.error(f"Error occurred in delete_attachment: {e}")
        return False


async def get_attachment(
    tid: str, /, user_id: str, message_id: str, attachment_id: str
):
    try:
        return mongo.read(
            UUIDBase62Cipher.encode(tid),
            Collection.ATT,
            {
                "user_id": user_id,
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
        )
    except Exception as e:
        logger.error(f"Error occurred in get_attachment: {e}")


async def get_all_attachments(tid: str, /, user_id: str, message_id: str) -> list[dict]:
    try:
        return mongo.read(
            UUIDBase62Cipher.encode(tid),
            Collection.ATT,
            {"user_id": user_id, "message_id": message_id},
        )
    except Exception as e:
        logger.error(f"Error occurred in get_attachments: {e}")
        return []
