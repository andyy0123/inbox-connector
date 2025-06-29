# Brownie
from common import AESCipher
from common import CIPHER_KEY
from services import dataService

def createTenant(appId, appSecret, tenatId, userlist):
    cipher = AESCipher(CIPHER_KEY)

    hashedAppId = cipher.encrypt(appId)
    hashedAppSecret = cipher.encrypt(appSecret)
    tenatName = cipher.encrypt(tenatId)

    if isinstance(userlist, dict):
        userlist = [userlist]

    dataService.createDB(tenatId, tenatName)
    dataService.creatCollection('info', tenatName, _id='singleton',appId=hashedAppId, appSecret=hashedAppSecret)
    dataService.creatCollection('users', tenatName, userlist=userlist)

def _getTenantInfo(tenatName):
    """ return json object"""
    doc = dataService.getDocument('info', tenatName, _id='singleton')
    return doc

def getTenantAccessToken(tenatName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenatName)

    if info and 'accessToken' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['accessToken'])

    return None

def getTenantAppId(tenatName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenatName)

    if info and 'appId' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appId'])

    return None

def getTenantAppSercret(tenatName):
    """ get access token from db
        return
            1. access token string (already decrypted)
            2. None, if not exist"""
    info = _getTenantInfo(tenatName)

    if info and 'appSercret' in info:
        cipher = AESCipher(CIPHER_KEY)
        return cipher.decrypt(info['appSercret'])

    return None

def getTenantUser(tenatName, userId):
    doc = None

    if userId:
        doc = dataService.getDocument('users', tenatName, userId=userId)
    else:
        doc = dataService.getAllDocuments('users', tenatName)

    return doc
