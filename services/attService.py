# Danny

from typing import Optional
from m365Connector import deleteAtt
from msgraph import GraphServiceClient
from authService import get_graph_client
from m365Connector import deleteAtt
from dataService import MongoDataService
from tenantService import TenantService
from collections.abc import 

tenant = None
mongo = MongoDataService()
Success = bool

def create_attachment(tid: str, /, user_id: str, message_id: str, attachment_id: str | list[str]) -> Success:
    is_attachment_array = hasattr(attachment_id, '__len__') and (not isinstance(attachment_id, str))

    try:
        if is_attachment_array:
            data = [{"user_id": user_id, "message_id": message_id, "attachment_id": att_id} for att_id in attachment_id] 
            mongo.create_many(tid, "attachment", data)
        else:
            data = {"user_id": user_id, "message_id": message_id, "attachment_id": attachment_id}
            mongo.create_one(tid, "attachment", data)
        return True
    except Exception as e:
        print(f"{e}")
        return False
    
    

async def delete_attachment(tid: str, /, user_id: str, message_id: str, attachment_id: str, request_to_m365: Optional[bool] = True):
    if tenant is None:
        tenant = TenantService(tid)
    client: GraphServiceClient = await get_graph_client(tid, tenant.getTenantAppId(), tenant.getTenantAppSecret())

    if request_to_m365:
        await deleteAtt(client, user_id, message_id, attachment_id)
    
    mongo.delete_one(tid, "attachment", {"user_id": user_id, "message_id": message_id, "attachment_id": attachment_id})


async def _do_database_delete_att():
    return {"success": True}
