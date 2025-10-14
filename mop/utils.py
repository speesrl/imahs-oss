import logging
import threading

from dataclasses import dataclass

@dataclass
class FileUpload:
    filename: str
    file: str 
    content_type: str
        
class Singleton(type):
    _instances = {}
    _lock = threading.Lock()
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ExceptionFormatter(logging.Formatter):
    def format(self, record):
        if record.exc_info:
            return f"Exception: {record.getMessage()}\n{self.formatException(record.exc_info)}"
        elif record.levelname == "ERROR":
            return f"Error: {record.getMessage()}\n"
        return super().format(record)
