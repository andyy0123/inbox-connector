import uvicorn
from fastapi import FastAPI, HTTPException, Body
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from services.logService import setup_logger
from services.authService import auth_init_tenant, TenantInitializationError, GraphAPIError, AlreadyInitializedError

app = FastAPI(
    title="M365 Inbox Connector", description="M365 Inbox Connector", version="1.0.0"
)

logger = setup_logger(__name__)

# --- Pydantic Model Definitions ---
class TenantCredentials(BaseModel):
    tenant_id: str = Field(..., description="The unique identifier for the tenant.")
    client_id: str = Field(..., description="The client ID (appId) for authentication.")
    client_secret: str = Field(..., description="The client secret (appSecret) for authentication.")

class TenantResponse(BaseModel):
    message: str
    tenant_id: str


@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "M365 Inbox Connector",
        "version": "1.0.0",
    }


# --- Custom Exception Handlers ---
@app.exception_handler(TenantInitializationError)
async def tenant_init_exception_handler(request, exc: TenantInitializationError):
    return JSONResponse(
        status_code=400, # Bad Request, as it might be an issue with the provided data
        content={"message": f"Tenant initialization failed: {exc}"},
    )


@app.exception_handler(GraphAPIError)
async def graph_api_exception_handler(request, exc: GraphAPIError):
    return JSONResponse(
        status_code=503, # Service Unavailable, indicating an external service issue
        content={"message": f"An error occurred while communicating with Microsoft Graph API: {exc}"},
    )


@app.post(
    "/init_tenant",
    response_model=TenantResponse,
    tags=["Tenants"],
    summary="Initialize a new tenant",
)
async def init_tenant(
    credentials: TenantCredentials = Body(...)
):
    try:
        logger.info(f"Received request to initialize tenant: {credentials.tenant_id}")

        # Execute initialization logic
        await auth_init_tenant(
            credentials.tenant_id,
            credentials.client_id,
            credentials.client_secret
        )

        return {
            "message": "Tenant has been initialized successfully",
            "tenant_id": credentials.tenant_id,
        }

    except AlreadyInitializedError as e:
        raise HTTPException(
            status_code=409,
            detail="Tenant has already been initialized."
        )

    # Maintain a generic server error handler without exposing internal details
    except Exception as e:
        logger.error(f"An unexpected error occurred while initializing tenant '{credentials.tenant_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected internal server error occurred."
        )


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
    uvicorn.run(app, host="127.0.0.0", port=8080)
