"""
Usage:
    from services.dataService import DataService
    data_service = DataService().get_data_service()

    # Example usage
    dataService.is_database_exists("123")

    dataService.create("123", "message", {"message": "Hello, World!"})

    dataService.create_many(
        "123",
        "message",
        [{"message": "Hello, World!"}, {"message": "Hello, World22222!"}],
    )

    dataService.read(
        "123", "message", {"_id": ObjectId("6862052ac17526c879cc0fce")}
    )

    dataService.update_one(
        "123",
        "message",
        {"_id": ObjectId("6862052ac17526c879cc0fce")},
        {"message": "Goodbye, World"},
    )

    dataService.delete_one(
        "123",
        "message",
        {"_id": ObjectId("686204ffd8578e617a242970")},
    )

    data_service.close()
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, PyMongoError

from logger.operationLogger import OperationLogger
from common.constants import LogLevel

logger = OperationLogger()
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017")


class MongoDataService:
    def __init__(self):
        """initialize"""
        self.connection_string = MONGODB_URL
        self.client: Optional[MongoClient] = None
        self._connect()

    def _connect(self):
        """connection"""
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=5,
            )
            self.client.admin.command("ping")
            logger.log(LogLevel.INFO, "MongoDB", "connected successfully")
        except ConnectionFailure as e:
            logger.log(LogLevel.ERROR, "MongoDB", f"connection failed: {e}")
            raise

    def _get_tenant_database(self, tenant_id: str) -> Database:
        """
        get tenant-specific database

        Args:
            tenant_id: tenant ID

        Returns:
            Database: tenant-specific database instance
        """
        if not self.client:
            raise ConnectionFailure("MongoDB not connected")

        db_name = f"tenant_{tenant_id}"

        logger.log(
            LogLevel.INFO, "MongoDB", f"connected successfully to database: {db_name}"
        )
        return self.client[db_name]

    def _get_collection(self, tenant_id: str, collection_type: str) -> Collection:
        """
        get tenant-specific collection

        Args:
            tenant_id: tenant ID
            collection_type: collection type

        Returns:
            Collection: collection instance
        """
        db = self._get_tenant_database(tenant_id)
        return db[collection_type]

    def is_database_exists(self, tenant_id: str) -> bool:
        """
        Check if a tenant-specific database exists.

        Args:
            tenant_id: tenant ID

        Returns:
            bool: True if the database exists, False otherwise
        """
        if not self.client:
            raise ConnectionFailure("MongoDB not connected")

        db_name = f"tenant_{tenant_id}"
        return db_name in self.client.list_database_names()

    def create(
        self, tenant_id: str, collection_type: str, document: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        create document

        Args:
            tenant_id: tenant ID
            collection_type: collection type
            document: document to create

        Returns:
            Dict[str, Any]: the created document
        """
        try:
            collection = self._get_collection(tenant_id, collection_type)

            document["created_at"] = datetime.now(timezone.utc)
            document["updated_at"] = datetime.now(timezone.utc)

            result = collection.insert_one(document)
            logger.log(
                LogLevel.INFO,
                "MongoDB",
                "created document successfully",
                tenant_id=tenant_id,
                collection_type=collection_type,
            )
            return str(result)

        except PyMongoError as e:
            logger.log(
                LogLevel.ERROR,
                "MongoDB",
                "create document failed",
                tenant_id=tenant_id,
                collection_type=collection_type,
                error=str(e),
            )
            raise

    def create_many(
        self, tenant_id: str, collection_type: str, documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        create multiple documents

        Args:
            tenant_id: tenant ID
            collection_type: collection type
            documents: list of documents to create

        Returns:
            List[Dict[str, Any]]: list of inserted document
        """
        try:
            collection = self._get_collection(tenant_id, collection_type)

            current_time = datetime.now(timezone.utc)
            for document in documents:
                document["created_at"] = current_time
                document["updated_at"] = current_time

            result = collection.insert_many(documents)
            logger.log(
                LogLevel.INFO,
                "MongoDB",
                f"created {len(result.inserted_ids)} documents successfully",
                tenant_id=tenant_id,
                collection_type=collection_type,
            )
            return result

        except PyMongoError as e:
            logger.log(
                LogLevel.ERROR,
                "MongoDB",
                "create multiple documents failed",
                tenant_id=tenant_id,
                collection_type=collection_type,
                error=str(e),
            )
            raise

    def read(
        self, tenant_id: str, collection_type: str, query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        read documents

        Args:
            tenant_id: tenant ID
            collection_type: collection type
            query: query conditions

        Returns:
            List[Dict[str, Any]]: query results
        """
        try:
            collection = self._get_collection(tenant_id, collection_type)

            cursor = collection.find(query)

            documents = []
            for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                documents.append(doc)

            logger.log(
                LogLevel.INFO,
                "MongoDB",
                f"Tenant {tenant_id} found {len(documents)} documents in {collection_type}",
            )
            return documents

        except PyMongoError as e:
            logger.log(LogLevel.ERROR, "MongoDB", f"query documents failed: {e}")
            raise

    def update_one(
        self,
        tenant_id: str,
        collection_type: str,
        query: Dict[str, Any],
        update_doc: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        update a document

        Args:
            tenant_id: tenant ID
            collection_type: collection type
            query: query conditions
            update_doc: update content

        Returns:
            Optional[Dict[str, Any]]: updated document or None if not found
        """
        try:
            collection = self._get_collection(tenant_id, collection_type)

            if "$set" not in update_doc:
                update_doc = {"$set": update_doc}

            if "$set" in update_doc:
                update_doc["$set"]["updated_at"] = datetime.now(timezone.utc)

            result = collection.update_one(query, update_doc)
            success = result.modified_count > 0

            if success:
                logger.log(
                    LogLevel.INFO,
                    "MongoDB",
                    "updated document successfully",
                    tenant_id=tenant_id,
                    collection_type=collection_type,
                )

            return result

        except PyMongoError as e:
            logger.log(
                LogLevel.ERROR,
                "MongoDB",
                f"update document failed: {e}",
                tenant_id=tenant_id,
                collection_type=collection_type,
            )
            raise

    def delete_one(
        self, tenant_id: str, collection_type: str, query: Dict[str, Any]
    ) -> bool:
        """
        delete a document

        Args:
            tenant_id: tenant ID
            collection_type: collection type
            query: query conditions

        Returns:
            bool: whether the delete was successful
        """
        try:
            collection = self._get_collection(tenant_id, collection_type)
            result = collection.delete_one(query)
            success = result.deleted_count > 0

            if success:
                logger.log(
                    LogLevel.INFO,
                    "MongoDB",
                    "deleted document successfully",
                    tenant_id=tenant_id,
                    collection_type=collection_type,
                )

            return success

        except PyMongoError as e:
            logger.log(
                LogLevel.ERROR,
                "MongoDB",
                f"delete document failed: {e}",
                tenant_id=tenant_id,
                collection_type=collection_type,
            )
            raise

    def close(self):
        """close connection"""
        if self.client:
            self.client.close()
            logger.log(LogLevel.INFO, "MongoDB", "closed connection")


class DataService:
    """DataService Singleton Class"""

    _instance = None
    _data_service = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_data_service(self) -> MongoDataService:
        """get data service instance"""
        if self._data_service is None:
            self._data_service = MongoDataService()
        return self._data_service

    def close(self):
        """close data service"""
        if self._data_service:
            self._data_service.close()
            self._data_service = None
