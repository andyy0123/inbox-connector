import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from services.routerService import router as tenant_router
from contextlib import asynccontextmanager

from services.dataService import DataService
from services.logService import setup_logger


data_service = None

app = FastAPI(
    title="Microsoft Graph Tenant API",
    description="An API to initialize, update, and manage tenant data from Microsoft Graph.",
    version="1.0.0"
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


# Generic exception handler to catch any unhandled errors
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An unexpected server error occurred: {exc}"},
    )

# Include the router with all our endpoints
app.include_router(tenant_router)

@app.get("/", tags=["Health Check"])
def read_root():
    """Root endpoint for health checks."""
    return {"status": "ok", "message": "Welcome to the Graph Tenant API"}

if __name__ == "__main__":
    # test To run: uvicorn main:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8000)
