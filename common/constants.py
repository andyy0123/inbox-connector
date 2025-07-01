from enum import Enum, IntEnum, unique
import os

@unique
class LogLevel(IntEnum):
    INFO = 1
    ERROR = 2
@unique
class Collection(Enum):
    INFO = 'info'
    USER = 'users'
    MAIL = 'mails'
    ATT = 'attachments'