from fastapi import FastAPI
import uvicorn
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from services.dataService import TenantDataService

data_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle"""
    global data_service

    print("Initializing data service...")
    data_service = TenantDataService()

    setup_test_data()
    print("Application startup complete")

    yield

    print("Application is shutting down...")


def setup_test_data():
    """Setup test data"""
    global data_service

    tenant_id = "company_abc_123"

    existing_tenant = data_service.read(tenant_id, "tenant_config")
    if existing_tenant:
        print(f"Tenant {tenant_id} already exists, skipping creation")
        return

    tenant_config = {
        "company_name": "ABC Corp",
        "m365_settings": {
            "tenant_id": "abc-corp-m365-tenant",
            "domains": ["abc.com", "abc.co.uk"],
        },
    }

    success = data_service.create_tenant(tenant_id, tenant_config)
    if success:
        print(f"Successfully created tenant: {tenant_id}")

        email_data = {
            "message_id": "msg_123",
            "sender_email": "sender@example.com",
            "subject": "Test Email",
            "received_datetime": datetime.now(timezone.utc),
            "has_attachments": True,
            "status": "processed",
        }

        email_id = data_service.create(tenant_id, "emails", email_data)
        print(f"Successfully created test email: {email_id}")


app = FastAPI(
    title="M365 Inbox Connector", description="M365 Inbox Connector", version="1.0.0"
)


@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
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
