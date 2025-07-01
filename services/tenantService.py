# Brownie
from common.cipher import AESCipher
from common.constants import CIPHER_KEY, Collection, LogLevel
from logger.operationLogger import OperationLogger
from services.dataService import DataService

logger = OperationLogger()
cipher = AESCipher(CIPHER_KEY)
mongo_service = DataService.get_data_service()

class TenantService:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        try:
            self.__tenant_hash = cipher.encrypt(tenant_id)
        except Exception as e:
            logger.log(LogLevel.ERROR, "TenantService", f"encrypt failed: {e}")
            raise
        
    def delete(self):
        mongo_service.delete_database(self.__tenant_hash)

    def getTenantHashed(self):
        return self.__tenant_hash

    def _create_info_data(self, cid, csecret):
        try:
            data = {
                'cid': cipher.encrypt(cid),
                'csecret': cipher.encrypt(csecret)
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
                return cipher.decrypt(info['cid'])
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
                return cipher.decrypt(info['csecret'])
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