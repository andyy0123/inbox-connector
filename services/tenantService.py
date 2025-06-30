# Brownie
from common.cipher import AESCipher
from common.constants import CIPHER_KEY
from common.constants import Collection
from logger.errorLogger import ErrorLogger
from services import dataService

def createTenant(appId, appSecret, tenantId, users, mails):
    errorLog = ErrorLogger()
    cipher = AESCipher(CIPHER_KEY)

    try:
        hashedAppId = cipher.encrypt(appId)
        hashedAppSecret = cipher.encrypt(appSecret)
        hashedTenant = cipher.encrypt(tenantId)
        
        data = {
        '_id': 'singleton',
        'appId': hashedAppId,
        'appSecret': hashedAppSecret
        }
        
        userList = users
        if isinstance(userList, dict):
            userList = [userList]
            
        mailList = mails
        if isinstance(mailList, dict):
            mailList = [mailList]

        dataService.createDB(tenantId, hashedTenant)
        dataService.creatDocument(Collection.INFO, hashedTenant, data)
        dataService.creatDocument(Collection.USER, hashedTenant, userList)
        
        return hashedTenant
    
    except Exception as e:
        errorLog.log('createTenant failed', err=e)
        return None   

def updateTenant(appId, appSecret, tenantId):
    

def _getTenantInfo(hashedTenant):
    """ return json object"""
    doc = dataService.getDocument('info', hashedTenant, _id='singleton')
    return doc

def getTenantAppId(hashedTenant):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(hashedTenant)

    if info and 'appId' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appId'])

    return None

def getTenantAppSercret(hashedTenant):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(hashedTenant)

    if info and 'appSercret' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appSercret'])

    return None

def getTenantUser(hashedTenant, userId):
    doc = None

    if userId:
        doc = dataService.getDocument('users', hashedTenant, userId=userId)
    else:
        doc = dataService.getAllDocuments('users', hashedTenant)

    return doc