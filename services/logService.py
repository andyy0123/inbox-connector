import logging


def setup_logger(name):
    # 設定 Formatter
    formatter = logging.Formatter(
        '[%(asctime)s][%(process)d][%(levelname)s][%(filename)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler('inbox_connector.log')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    # for console log
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    # 避免重複加 handler
    if not logger.handlers:
        logger.addHandler(ch)
        logger.addHandler(fh)
    return logger