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
    title="M365 Inbox Connector",
    description="M365 Inbox Connector",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "M365 Inbox Connector",
        "version": "1.0.0"
    }


@app.get("/tenant/{tenant_id}")
async def getTenant(tenant_id: str):
    """Get tenant information"""
    tenant_info = data_service.read(tenant_id, "tenant_config")
    if not tenant_info:
        return {"error": "Tenant not found"}, 404
    return tenant_info

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
