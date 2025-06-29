# Brownie
from common import AESCipher
from common import CIPHER_KEY
from services import dataService

def createTenant(appId, appSecret, tenantId, userlist):
    cipher = AESCipher(CIPHER_KEY)

    hashedAppId = cipher.encrypt(appId)
    hashedAppSecret = cipher.encrypt(appSecret)
    tenantName = cipher.encrypt(tenantId)

    if isinstance(userlist, dict):
        userlist = [userlist]

    dataService.createDB(tenantId, tenantName)
    dataService.creatCollection('info', tenantName, _id='singleton',appId=hashedAppId, appSecret=hashedAppSecret)
    dataService.creatCollection('users', tenantName, userlist=userlist)

def _getTenantInfo(tenantName):
    """ return json object"""
    doc = dataService.getDocument('info', tenantName, _id='singleton')
    return doc

def getTenantAccessToken(tenantName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenantName)

    if info and 'accessToken' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['accessToken'])

    return None

def getTenantAppId(tenantName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenantName)

    if info and 'appId' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appId'])

    return None

def getTenantAppSercret(tenantName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenantName)

    if info and 'appSercret' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appSercret'])

    return None

def getTenantUser(tenantName, userId):
    doc = None

    if userId:
        doc = dataService.getDocument('users', tenantName, userId=userId)
    else:
        doc = dataService.getAllDocuments('users', tenantName)

    return doc