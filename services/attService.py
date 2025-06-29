# Danny

from m365Connector import deleteAtt
from msgraph import GraphServiceClient


def createAttachment():
    pass


async def deleteAttachment(cid: str, csec: str, tid: str):
    client: GraphServiceClient = getClientFromCache(cid, csec, tid)
    await deleteAtt(client)
    _do_database_delete_att()


async def _do_database_delete_att():
    return {"success": True}
