import json
import logging
import sys
import traceback
from typing import Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    return root


def log_error(contexto: str, ex: Exception, correlation_id: Optional[str] = None):
    logger = logging.getLogger()
    extra = {"correlation_id": correlation_id} if correlation_id else {}
    logger.error(f"[{contexto}] {ex}", extra=extra, exc_info=True)


def log_info(message: str, correlation_id: Optional[str] = None):
    logger = logging.getLogger()
    extra = {"correlation_id": correlation_id} if correlation_id else {}
    logger.info(message, extra=extra)
