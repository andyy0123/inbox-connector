from enum import IntEnum, unique

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
    