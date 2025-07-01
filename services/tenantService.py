import keyring
import base64
from Crypto.Random import get_random_bytes
from common.cipher import AESCipher, UUIDBase62Cipher
from common.constants import Collection, LogLevel
from logger.operationLogger import OperationLogger
from services.dataService import DataService

KEY_LENGTH = 16
KEY_NAME = "AES_KEY"

logger = OperationLogger()
dataService = DataService()
mongo_service = dataService.get_data_service()

class TenantService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        try:
            self.__tenant_hash = UUIDBase62Cipher.encode(tenant_id)
            self.__aes_cipher = AESCipher(self._get_aes_key())
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"init failed: {e}")
            raise

    def _get_aes_key(self):
        try:
            key_b64 = keyring.get_password(self.__tenant_hash, KEY_NAME)
            if key_b64 is None:
                key_bytes = get_random_bytes(KEY_LENGTH)
                key_b64 = base64.b64encode(key_bytes).decode('utf-8')
                keyring.set_password(self.__tenant_hash, KEY_NAME, key_b64)
            else:
                key_bytes = base64.b64decode(key_b64)
            return key_bytes
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"_get_aes_key failed: {e}")
            raise
        
    def delete(self):
        mongo_service.delete_database(self.__tenant_hash)

    def getTenantHashed(self):
        return self.__tenant_hash

    def _create_info_data(self, cid, csecret):
        try:
            data = {
                'cid': self.__aes_cipher.encrypt(cid),
                'csecret': self.__aes_cipher.encrypt(csecret)
            }
            
            return data
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"_create_info_data failed: {e}")
            raise

    def createTenant(self, cid, csecret):
        data = self._create_info_data(cid, csecret)
        
        if data :
            data['_id'] = 'singleton'
            mongo_service.create_one(self.__tenant_hash, Collection.INFO, data)
            return True
    
        return False   

    def updateTenant(self, cid, csecret):
        data = self._create_info_data(cid, csecret)
        
        if data :
            mongo_service.update_one(self.__tenant_hash, Collection.INFO, {'_id' : 'singleton'}, {"$set": data})
            return True
    
        return False
    
    def checkTenantExist(self):
        return mongo_service.is_database_exists(self.__tenant_hash)
    
    def _getTenantInfo(self):
        """ return json object"""
        doc = mongo_service.read(self.__tenant_hash, Collection.INFO,{"_id" : "singleton"})
        return doc[0] if doc else None

    def getTenantAppId(self):
        """ return
                1. app id string (already decrypted)
                2. None, if not exist"""
        info = self._getTenantInfo()

        if info and 'cid' in info:
            try:
                return self.__aes_cipher.decrypt(info['cid'])
            except Exception as e:
                logger.log(LogLevel.ERROR, "TenantService", f"decrypt app id failed: {e}")
                raise

        return None

    def getTenantAppSecret(self):
        """ return
            1. app secret string (already decrypted)
            2. None, if not exist"""
        info = self._getTenantInfo()

        if info and 'csecret' in info:
            try:
                return self.__aes_cipher.decrypt(info['csecret'])
            except Exception as e:
                logger.log(LogLevel.ERROR, "TenantService", f"decrypt app secret failed: {e}")
                raise

        return None

    def getTenantUser(self, user_id=None):
        query = {"user_id": user_id} if user_id else {}
        return mongo_service.read(self.__tenant_hash, Collection.USER, query)

    def insertUserList(self, userList):
        if not isinstance(userList, list):
            raise ValueError("userList must be a list of dict")
        mongo_service.create_many(self.__tenant_hash, Collection.USER, userList)