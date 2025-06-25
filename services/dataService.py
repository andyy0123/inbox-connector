import os
from pymongo import MongoClient
from typing import Any, Dict, List, Optional
import hashlib
from datetime import datetime, timezone

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017")
DB_NAME = "inbox_connector_db"


class TenantDataService:
    """
    tenant data service: collection-per-tenant
    """

    def __init__(self):
        """initialize the service with MongoDB connection"""
        self.client = MongoClient(MONGODB_URL)
        self.database = self.client[DB_NAME]

    def _get_tenant_collection_name(self, tenant_id: str, collection_name: str) -> str:
        """Generate a tenant-specific collection name."""
        tenant_hash = hashlib.md5(tenant_id.encode()).hexdigest()[:8]
        return f"tenant_{tenant_hash}_{collection_name}"

    def _get_collection(self, tenant_id: str, collection_name: str):
        """Get the tenant-specific collection."""
        if not tenant_id:
            raise ValueError("tenant_id is required")

        tenant_collection_name = self._get_tenant_collection_name(
            tenant_id, collection_name
        )
        return self.database[tenant_collection_name]

    def _add_audit_fields(
        self, document: Dict[str, Any], tenant_id: str, operation: str
    ) -> Dict[str, Any]:
        """Add audit fields."""
        document = document.copy()
        document.update(
            {
                "tenant_id": tenant_id,  # Double insurance
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "operation": operation,
            }
        )
        return document

    def create_tenant(self, tenant_id: str, tenant_config: Dict[str, Any]) -> bool:
        """
        Create tenant configuration

        Args:
            tenant_id: Tenant ID
            tenant_config: Tenant configuration data
        """
        collection = self._get_collection(tenant_id, "tenant_config")

        existing = collection.find_one({"tenant_id": tenant_id})
        if existing:
            return False

        config_doc = self._add_audit_fields(tenant_config, tenant_id, "create_tenant")
        collection.insert_one(config_doc)

        self._create_tenant_indexes(tenant_id)

        return True

    def _create_tenant_indexes(self, tenant_id: str):
        """Create necessary indexes for the new tenant"""
        collections_indexes = {
            "emails": [
                ("tenant_id", 1),
                ("message_id", 1),  # M365 Message ID
                ("received_datetime", -1),
                ("sender_email", 1),
            ],
            "sync_status": [("tenant_id", 1), ("last_sync_time", -1)],
            "operations": [
                ("tenant_id", 1),
                ("operation_time", -1),
                ("operation_type", 1),
            ],
        }

        for collection_name, indexes in collections_indexes.items():
            collection = self._get_collection(tenant_id, collection_name)
            for index in indexes:
                collection.create_index([index])

    def create(
        self, tenant_id: str, collection_name: str, document: Dict[str, Any]
    ) -> str:
        """
        Create a document

        Args:
            tenant_id: tenant ID
            collection_name: Collection name
            document: Document to create
        """
        collection = self._get_collection(tenant_id, collection_name)

        document_with_audit = self._add_audit_fields(document, tenant_id, "create")

        result = collection.insert_one(document_with_audit)
        return str(result.inserted_id)

    def read(
        self,
        tenant_id: str,
        collection_name: str,
        query: Dict[str, Any] = None,
        limit: Optional[int] = None,
        sort: Optional[List[tuple]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read documents

        Args:
            tenant_id: tenant ID
            collection_name: Collection name
            query: Query conditions
            limit: Limit the number of returned documents
            sort: Sort conditions
        """
        collection = self._get_collection(tenant_id, collection_name)

        if query is None:
            query = {}
        query["tenant_id"] = tenant_id

        cursor = collection.find(query)

        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)

        return list(cursor)

    def update(
        self,
        tenant_id: str,
        collection_name: str,
        query: Dict[str, Any],
        update_data: Dict[str, Any],
    ) -> int:
        """
        Update documents

        Args:
            tenant_id: tenant ID
            collection_name: Collection name
            query: Query conditions
            update_data: Update data
        """
        collection = self._get_collection(tenant_id, collection_name)

        query["tenant_id"] = tenant_id

        update_data["updated_at"] = datetime.now(timezone.utc)

        result = collection.update_many(query, {"$set": update_data})
        return result.modified_count

    def delete(
        self, tenant_id: str, collection_name: str, query: Dict[str, Any]
    ) -> int:
        """
        Delete documents

        Args:
            tenant_id: tenant ID
            collection_name: Collection name
            query: Query conditions
        """
        collection = self._get_collection(tenant_id, collection_name)

        query["tenant_id"] = tenant_id

        result = collection.delete_many(query)
        return result.deleted_count
