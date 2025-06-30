import uvicorn
from fastapi import FastAPI, HTTPException, Body
from datetime import datetime
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from services.dataService import DataService
from services.logService import setup_logger
from services.authService import (
    auth_init_tenant,
    auth_update_tenant,
    TenantInitializationError,
    TenantUpdateError,
    GraphAPIError,
    AlreadyInitializedError,
    TenantNotFoundError,
)

data_service = None

app = FastAPI(
    title="M365 Inbox Connector", description="M365 Inbox Connector", version="1.0.0"
)

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """application lifecycle"""
    global data_service

    print("Initializing data service...")

    data_service = DataService().get_data_service()

    print("Application startup complete")

    yield

    print("Application is shutting down...")


# --- Pydantic Model Definitions ---
class TenantCredentials(BaseModel):
    tenant_id: str = Field(..., description="The unique identifier for the tenant.")
    client_id: str = Field(..., description="The client ID (appId) for authentication.")
    client_secret: str = Field(
        ..., description="The client secret (appSecret) for authentication."
    )


class TenantResponse(BaseModel):
    message: str
    tenant_id: str

class TenantUpdateResponse(BaseModel):
    message: str
    tenant_id: str
    updated_at: datetime


@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(),
        "service": "M365 Inbox Connector",
        "version": "1.0.0",
    }


# --- Custom Exception Handlers ---
@app.exception_handler(TenantNotFoundError)
async def tenant_not_found_exception_handler(request, exc: TenantNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )

@app.exception_handler(AlreadyInitializedError)
async def tenant_already_initialized_exception_handler(request, exc: AlreadyInitializedError):
    return JSONResponse(
        status_code=409,
        content={"message": str(exc)},
    )
@app.exception_handler(TenantInitializationError)
async def tenant_init_exception_handler(request, exc: TenantInitializationError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Tenant initialization failed: {exc}"},
    )

@app.exception_handler(TenantUpdateError)
async def tenant_update_exception_handler(request, exc: TenantUpdateError):
    return JSONResponse(
        status_code=400,
        content={"message": f"Tenant update failed: {exc}"},
    )

@app.exception_handler(GraphAPIError)
async def graph_api_exception_handler(request, exc: GraphAPIError):
    return JSONResponse(
        status_code=503,
        content={
            "message": f"An error occurred while communicating with Microsoft Graph API: {exc}"
        },
    )


@app.post(
    "/tenant/init",
    response_model=TenantResponse,
    tags=["Tenants"],
    summary="Initialize a new tenant",
    description="Initializes a new tenant by validating credentials against the Graph API, fetching user and mail data, and storing the configuration.",
    status_code=201, # 201 Created is more appropriate for successful resource creation.
)
async def init_tenant(credentials: TenantCredentials = Body(...)):
    """
    Initializes a new tenant.
    - Validates credentials with Microsoft Graph.
    - Fetches initial data.
    - Raises 409 Conflict if the tenant is already initialized.
    """
    try:
        logger.info(f"Received request to initialize tenant: {credentials.tenant_id}")

        # Execute initialization logic
        await auth_init_tenant(
            credentials.tenant_id, credentials.client_id, credentials.client_secret
        )

        return {
            "message": "Tenant has been initialized successfully",
            "tenant_id": credentials.tenant_id,
        }

    except AlreadyInitializedError as e:
        raise HTTPException(
            status_code=409, detail="Tenant has already been initialized."
        )

    # Maintain a generic server error handler without exposing internal details
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while initializing tenant '{credentials.tenant_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="An unexpected internal server error occurred."
        )


@app.post(
    "/tenant/update",
    response_model=TenantUpdateResponse,
    tags=["Tenants"],
    summary="Update an existing tenant's credentials",
    description="Updates the client_id and client_secret for an existing tenant after validating the new credentials.",
)
async def update_tenant_api(credentials: TenantCredentials = Body(...)):
    """
    Updates an existing tenant's credentials.
    - Raises 404 Not Found if the tenant does not exist.
    - Validates the new credentials before saving them.
    """
    try:
        logger.info(f"Received request to update tenant: {credentials.tenant_id}")
        updated_timestamp = await auth_update_tenant(
            credentials.tenant_id, credentials.client_id, credentials.client_secret
        )
        return {
            "message": "Tenant credentials have been updated successfully",
            "tenant_id": credentials.tenant_id,
            "updated_at": updated_timestamp,
        }
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating tenant '{credentials.tenant_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected internal server error occurred.")


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
