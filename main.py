from fastapi import FastAPI
import uvicorn
from datetime import datetime
from contextlib import asynccontextmanager

from services.dataService import DataService

data_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle"""
    global data_service

    print("Initializing data service...")

    data_service = DataService().get_data_service()

    print("Application startup complete")

    yield

    print("Application is shutting down...")


app = FastAPI(
    title="M365 Inbox Connector", description="M365 Inbox Connector", version="1.0.0"
)


@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(),
        "service": "M365 Inbox Connector",
        "version": "1.0.0",
    }


@app.get("/init_tenant")
async def init_tenant():
    """Init tenant 給 appId appSecret tenantId -> createTenant({appId, appSecret, tenantId, userList..}) ->
    getMail, getAtt -> response mongoTenantId"""
    return {"tenantMongoId": "Tenant initialized successfully"}


@app.get("/list_latest_mail")
async def list_latest_mail():
    """input: tenantMongoId, by tenant/user, output: latestMailList"""
    return {
        "latestMailList": [{"messageId": 1, "userId": 1, "attachments": []}],
        "status": "success",
    }


@app.get("/delete_mail")
async def delete_mail():
    """input: tenantMongoId, userId, messageId, output: delete: 1/0, 更新 mail"""
    return {"delete": 1}


@app.get("/delete_attachment")
async def delete_attachment():
    """input: tenantMongoId, userId, attachmentId, output: delete: 1/0, 更新 mail"""
    return {"delete": 1}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
