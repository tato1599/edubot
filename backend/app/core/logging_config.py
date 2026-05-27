"""
Configuracion de logging profesional con formato JSON para produccion.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict

from backend.app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formatter que emite logs en formato JSON para analisis estructurado."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Incluir extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime", "request_id"
            }:
                log_obj[key] = value
        
        return json.dumps(log_obj, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """Configura el logging global de la aplicacion."""
    
    # Remover handlers existentes
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Handler a stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    if settings.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Reducir verbosidad de librerias de terceros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
