from logger.basicLogger import BasicLogger


class OperationLogger:
    def __init__(self, log_file='operation.log'):
        self.BasicLogger = BasicLogger(log_file = log_file)

    def log(self, log_level, operation, msg, **kwargs):
        """ 支援彈性參數，讓所有操作類型都能塞入自己要的欄位
            ex.
                logger = OperationLogger()
                logger.log(LogLevel.ERROR, 'deleteMail', 'timeout', user='mail789')
                => [2025-06-26 16:56:01] [12345] [ERROR] [deleteMail] timeout (user=mail789)"""
        details = ''
        if kwargs:
            details = '(' + ', '.join(f'{k}={v}' for k, v in kwargs.items()) + ')'
        msg = (
            f"[{operation}] {msg} {details}"
        ).strip()
        
        self.BasicLogger.log(log_level, msg)