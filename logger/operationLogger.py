from logger.basicLogger import BasicLogger
from common.constants import OperationCode

class OperationLogger:
    OPERATION_MAP = {
        OperationCode.LOGIN: 'LOGIN',
        OperationCode.FETCH_MAIL: 'FETCH_MAIL',
        OperationCode.DELETE_MAIL: 'DELETE_MAIL',
        OperationCode.DELETE_ATTACHMENT: 'DELETE_ATTACHMENT',
    }
        
    def __init__(self, log_file='operation.log'):
        self.BasicLogger = BasicLogger(log_file = log_file)

    def log(self, log_level, operation_code, msg, **kwargs):
        """ 支援彈性參數，讓所有操作類型都能塞入自己要的欄位
            ex.
                logger = OperationLogger()
                logger.log(LogLevel.ERROR, OperationCode.LOGIN, 'timeout', user='mail789')
                => [2025-06-26 16:56:01] [12345] [ERROR] [LOGIN] timeout (user=mail789)"""
        details = ''
        if kwargs:
            details = '(' + ', '.join(f'{k}={v}' for k, v in kwargs.items()) + ')'
        operation = self.OPERATION_MAP.get(operation_code, f'UNKNOWN({operation_code})')
        msg = (
            f"[{operation}] {msg} {details}"
        ).strip()
        
        self.BasicLogger.log(log_level, msg)