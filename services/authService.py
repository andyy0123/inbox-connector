import json
import asyncio
from aiocache import cached, SimpleMemoryCache
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from services.logService import setup_logger
from services.m365Connector import getTenantUserList, getTenantAllMails


logger = setup_logger(__name__)


# --- Custom Exceptions ---
class TenantInitializationError(Exception):
    """For business logic errors during the initialization process."""
    pass

class GraphAPIError(Exception):
    """For wrapping errors from the Graph API."""
    pass

class AlreadyInitializedError(Exception):
    pass


@cached(ttl=3600, cache=SimpleMemoryCache)
async def get_graph_client(tenant_id: str, client_id: str, client_secret: str) -> GraphServiceClient:
    """Caches GraphServiceClient instances to avoid recreation."""
    logger.info(f"Creating a new GraphServiceClient instance for tenant {tenant_id}.")
    try:
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        client = GraphServiceClient(credentials=credential, scopes=['https://graph.microsoft.com/.default'])
        # Added: Immediately test the connection to trigger authentication errors
        await client.users.get()
        return client
    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed for tenant {tenant_id}: {e}")
        raise GraphAPIError("Authentication failed. Please check Tenant ID, Client ID, and Client Secret.")
    except Exception as e:
        logger.error(f"An unknown error occurred while creating GraphServiceClient: {e}")
        raise GraphAPIError(f"An unknown error occurred while creating the client: {e}")


# change start
async def save_data_to_json(data: dict, filename: str):
    """Saves data to a specified JSON file."""
    logger.info(f"Saving data to {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Data successfully saved to {filename}.")
        return filename
    except IOError as e:
        logger.error(f"Failed to write to file {filename}: {e}")
        raise
# change end


async def auth_init_tenant(tenant_id: str, client_id: str, client_secret: str) -> str:
    """
    Initializes a tenant, fetches data, and saves it. Returns the file path on success.
    """
    try:
        # change start
        import os
        output_filename = f"{tenant_id}_graph_data.json"
        if os.path.exists(output_filename):
            logger.info(f"Data file already exists for tenant {tenant_id}. Skipping data fetch.")
            raise AlreadyInitializedError(f"Tenant {tenant_id} already initialized.")
        # change end

        client = await get_graph_client(tenant_id, client_id, client_secret)

        logger.info(f"Starting to fetch user and mail data in parallel for tenant {tenant_id}...")
        tasks = [
            getTenantUserList(client),
            getTenantAllMails(client)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        users, mail_results = results

        # Check and handle errors from parallel tasks
        if isinstance(users, Exception):
            raise GraphAPIError(f"Failed to fetch user list: {users}")
        if isinstance(mail_results, Exception):
            raise GraphAPIError(f"Failed to fetch mail: {mail_results}")

        logger.info(f"Successfully fetched {len(users)} users.")

        if not users:
            logger.warning(f"No users found in tenant {tenant_id}.")
            raise TenantInitializationError("No users found, initialization aborted.")

        final_data = {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "users": users,
            "mails": mail_results
        }

        # change start
        # Save to file and return the file path
        await save_data_to_json(final_data, output_filename)
        # change end

    except ODataError as e:
        logger.error(f"Microsoft Graph API error: {e.error.code} - {e.error.message}")
        raise GraphAPIError(f"API request failed: {e.error.message}")

    # Re-raise already handled custom exceptions
    except (TenantInitializationError, GraphAPIError, AlreadyInitializedError) as e:
        raise e

    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during the initialization process: {e}", exc_info=True)
        # Wrap in a generic error to avoid leaking details
        raise TenantInitializationError("An unknown internal error occurred.")