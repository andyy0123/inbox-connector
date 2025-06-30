import datetime
import os
from common.constants import LogLevel


class BasicLogger:
    LEVEL_MAP = {
        LogLevel.INFO: "INFO",
        LogLevel.ERROR: "ERROR",
    }

    def __init__(self, log_file=None):
        self.log_file = log_file
        self.pid = os.getpid()

    def _write(self, level, msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{self.pid}] [{level}] {msg}"
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def log(self, log_level, msg):
        level = self.LEVEL_MAP.get(log_level, f"UNKNOWN({log_level})")
        self._write(level, msg)
