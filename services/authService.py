import json
import asyncio
from aiocache import cached, SimpleMemoryCache
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from services.logService import setup_logger
from services.m365Connector import getTenantUserList, getTenantAllMails

from services.mailService import getMail
from services.tenantService import TenantService


logger = setup_logger(__name__)


# --- Custom Exceptions ---
class TenantInitializationError(Exception):
    """For business logic errors during the initialization process."""

    pass


class GraphAPIError(Exception):
    """For wrapping errors from the Graph API."""

    pass


class AlreadyInitializedError(Exception):
    """Raised when trying to initialize a tenant that already exists."""

    pass


class TenantUpdateError(Exception):
    """For business logic errors during the update process."""

    pass


class TenantNotFoundError(Exception):
    """Raised when an operation is attempted on a non-existent tenant."""

    pass


class UserNotFoundError(Exception):
    """Raised when a specific user is not found within a tenant's data."""

    pass


class MailNotFoundError(Exception):
    """Raised when a specific mail is not found for a user."""

    pass


@cached(ttl=3600, cache=SimpleMemoryCache)
async def get_graph_client(
    tenant_id: str, client_id: str, client_secret: str
) -> GraphServiceClient:
    """
    Creates and caches a GraphServiceClient instance for a given tenant.
    Validates credentials by making a test API call.
    """
    logger.info(f"Creating a new GraphServiceClient instance for tenant {tenant_id}.")
    try:
        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )
        client = GraphServiceClient(
            credentials=credential, scopes=["https://graph.microsoft.com/.default"]
        )
        await client.users.get()
        return client
    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed for tenant {tenant_id}: {e}")
        raise GraphAPIError(
            "Authentication failed. Please check Tenant ID, Client ID, and Client Secret."
        )
    except Exception as e:
        logger.error(
            f"An unknown error occurred while creating GraphServiceClient: {e}"
        )
        raise GraphAPIError(f"An unknown error occurred while creating the client: {e}")


# --- Core Service Functions ---
async def auth_init_tenant(tenant_id: str, client_id: str, client_secret: str) -> None:
    """
    Initializes a tenant, fetches data, and saves it.
    """
    tenant_service = TenantService(tenant_id)

    if tenant_service.checkTenantExist():
        logger.info(
            f"Data file already exists for tenant {tenant_id}. Skipping data fetch."
        )
        raise AlreadyInitializedError(f"Tenant {tenant_id} already initialized.")

    try:
        client = await get_graph_client(tenant_id, client_id, client_secret)

        logger.info(f"Fetching user and mail data for tenant {tenant_id}...")
        tenant_service.createTenant(client_id, client_secret)
        await getMail(client, tenant_id)
        users = await getTenantUserList(client)

        if not users:
            logger.warning(f"No users found in tenant {tenant_id}.")
            raise TenantInitializationError("No users found, initialization aborted.")

        tenant_service.insertUserList(users)

        logger.info(f"Successfully fetched {len(users)} users.")

    except ODataError as e:
        logger.error(f"Microsoft Graph API error: {e.error.code} - {e.error.message}")
        raise GraphAPIError(f"API request failed: {e.error.message}")

    # Re-raise already handled custom exceptions
    except (TenantInitializationError, GraphAPIError, AlreadyInitializedError) as e:
        raise e

    except Exception as e:
        logger.critical(
            f"Unexpected error during initialization for tenant '{tenant_id}': {e}",
            exc_info=True,
        )
        # Wrap in a generic error to avoid leaking details
        raise TenantInitializationError("An unknown internal error occurred.")


async def auth_update_tenant(tenant_id: str, client_id: str, client_secret: str) -> str:
    """
    Updates a tenant's credentials after validating them.
    Returns the timestamp of the update.
    """

    tenant_service = TenantService(tenant_id)

    if not tenant_service.checkTenantExist():
        logger.info(f"Tenant {tenant_id} not initialized, cannot update.")
        raise TenantUpdateError(f"Tenant {tenant_id} not initialized.")

    try:
        tenant_service.updateTenant(client_id, client_secret)

    except (GraphAPIError, TenantNotFoundError) as e:
        # Re-raise validation and not-found errors directly.
        raise e
    except Exception as e:
        logger.critical(
            f"An unexpected critical error occurred during the update process for '{tenant_id}': {e}",
            exc_info=True,
        )
        raise TenantUpdateError(
            "An unknown internal error occurred during the update process."
        )
