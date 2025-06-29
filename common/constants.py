from enum import IntEnum, unique
import os

@unique
class OperationCode(IntEnum):
    LOGIN = 1
    FETCH_MAIL = 2
    DELETE_MAIL = 3
    DELETE_ATTACHMENT = 4
    
@unique
class LogLevel(IntEnum):
    INFO = 1
    ERROR = 2

CIPHER_KEY = os.environ['AES_SECRET_KEY'].encode('utf-8')