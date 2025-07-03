import keyring
import base64
from keyrings.alt.file import PlaintextKeyring
from Crypto.Random import get_random_bytes
from common.cipher import AESCipher, UUIDBase62Cipher
from common.constants import Collection, LogLevel
from logger.operationLogger import OperationLogger
from services.dataService import DataService

KEY_LENGTH = 16
KEY_NAME = "INOBX_CONNECTOR"

logger = OperationLogger()
dataService = DataService()
mongo_service = dataService.get_data_service()


class TenantService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        try:
            self.__tenant_hash = UUIDBase62Cipher.encode(tenant_id)
            self.__aes_cipher = AESCipher(self._get_aes_key())
            logger.log(LogLevel.INFO, "TenantService", f"init success")
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"init failed: {e}")
            raise

    def _get_aes_key(self):
        try:
            keyring.set_keyring(PlaintextKeyring())
            key_b64 = keyring.get_password(self.__tenant_hash, KEY_NAME)
            if key_b64 is None:
                key_bytes = get_random_bytes(KEY_LENGTH)
                key_b64 = base64.b64encode(key_bytes).decode("utf-8")
                keyring.set_password(self.__tenant_hash, KEY_NAME, key_b64)
            else:
                key_bytes = base64.b64decode(key_b64)
            return key_bytes
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"_get_aes_key failed: {e}")
            raise

    def delete(self):
        logger.log(
            LogLevel.INFO, "TenantService", f"delete database", name=self.__tenant_hash
        )
        mongo_service.delete_database(self.__tenant_hash)

    def getTenantHashed(self):
        return self.__tenant_hash

    def _create_info_data(self, cid, csecret):
        try:
            data = {
                "cid": self.__aes_cipher.encrypt(cid),
                "csecret": self.__aes_cipher.encrypt(csecret),
            }

            return data
        except Exception as e:
            logger.log(
                LogLevel.ERROR, "TenantService", f"_create_info_data failed: {e}"
            )
            raise

    def createTenant(self, cid, csecret):
        data = self._create_info_data(cid, csecret)

        if data:
            data["_id"] = "singleton"
            mongo_service.create_one(self.__tenant_hash, Collection.INFO, data)
            logger.log(
                LogLevel.INFO,
                "TenantService",
                f"create success",
                name=self.__tenant_hash,
            )
            return True

        return False

    def updateTenant(self, cid, csecret):
        data = self._create_info_data(cid, csecret)

        if data:
            mongo_service.update_one(
                self.__tenant_hash,
                Collection.INFO,
                {"_id": "singleton"},
                {"$set": data},
            )
            logger.log(
                LogLevel.INFO,
                "TenantService",
                f"update success",
                name=self.__tenant_hash,
            )
            return True

        return False

    def checkTenantExist(self):
        return mongo_service.is_database_exists(self.__tenant_hash)

    def _getTenantInfo(self):
        """return json object"""
        doc = mongo_service.read(
            self.__tenant_hash, Collection.INFO, {"_id": "singleton"}
        )
        return doc[0] if doc else None

    def getTenantAppId(self):
        """return
        1. app id string (already decrypted)
        2. None, if not exist"""
        info = self._getTenantInfo()

        if info and "cid" in info:
            try:
                return self.__aes_cipher.decrypt(info["cid"])
            except Exception as e:
                logger.log(
                    LogLevel.ERROR, "TenantService", f"decrypt app id failed: {e}"
                )
                raise

        return None

    def getTenantAppSecret(self):
        """return
        1. app secret string (already decrypted)
        2. None, if not exist"""
        info = self._getTenantInfo()

        if info and "csecret" in info:
            try:
                return self.__aes_cipher.decrypt(info["csecret"])
            except Exception as e:
                logger.log(
                    LogLevel.ERROR, "TenantService", f"decrypt app secret failed: {e}"
                )
                raise

        return None

    def getTenantUser(self, user_id=None):
        """if user_id in None return all users"""
        query = {"id": user_id} if user_id else {}
        return mongo_service.read(self.__tenant_hash, Collection.USER, query)

    def getTenantUseDeltaLink(self, user_id):
        if not user_id:
            raise ValueError("user_id error")

        doc = self.getTenantUser(user_id)
        if doc and "delta_link" in doc[0]:
            return doc[0]["delta_link"]

        return ""

    def updateTenantUser(self, user_id, **kwargs):
        """example: tenantService.updateTenantUser("abc@d.com", delta_link="www")"""
        if not user_id:
            raise ValueError("user_id error")

        if not kwargs:
            raise ValueError("please provide one field at least")

        data = {"$set": kwargs}
        mongo_service.update_one(
            self.__tenant_hash, Collection.USER, {"user_id": user_id}, data
        )
        logger.log(
            LogLevel.INFO,
            "TenantService",
            f"update user success",
            user_id=user_id,
            update_fields=list(kwargs.keys()),
        )

    def updateTenantUserDeltaLink(self, user_id, delta_link):
        if not user_id:
            raise ValueError("user_id error")

        if delta_link is None:
            raise ValueError("delta_link is None")

        self.updateTenantUser(user_id, delta_link=delta_link)

    def deleteTenantUser(self, user_id):
        if not user_id:
            raise ValueError("user_id error")

        mongo_service.delete_one(
            self.__tenant_hash, Collection.USER, {"user_id": user_id}
        )
        logger.log(
            LogLevel.INFO, "TenantService", f"delete user success", user_id=user_id
        )

    def insertUserList(self, userList):
        if not isinstance(userList, list):
            raise ValueError("userList must be a list of dict")

        mongo_service.create_many(self.__tenant_hash, Collection.USER, userList)
        logger.log(
            LogLevel.INFO,
            "TenantService",
            f"insert user list success",
            name=self.__tenant_hash,
        )
