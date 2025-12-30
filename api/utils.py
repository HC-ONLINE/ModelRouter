"""
Utilidades comunes: logging estructurado, generación de IDs, etc.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Any
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Formatter personalizado para logs JSON estructurados."""
    
    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        
        # Añadir timestamp en formato ISO
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Añadir nivel
        log_record['level'] = record.levelname
        
        # Añadir nombre del logger
        log_record['logger'] = record.name


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configura el sistema de logging con formato JSON estructurado.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Eliminar handlers existentes
    logger.handlers.clear()
    
    # Handler para stdout con formato JSON
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def generate_request_id() -> str:
    """
    Genera un ID único para tracking de requests.
    
    Returns:
        UUID en formato string
    """
    return str(uuid.uuid4())


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitiza datos sensibles antes de loggear.
    Elimina o enmascara claves API y otros datos sensibles.
    
    Args:
        data: Diccionario con datos a sanitizar
        
    Returns:
        Diccionario sanitizado
    """
    sensitive_keys = ['api_key', 'authorization', 'password', 'token', 'secret']
    sanitized = data.copy()
    
    for key in sanitized:
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = "***REDACTED***"
    
    return sanitized


class RequestLogger:
    """Logger contextual para requests individuales."""
    
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
    
    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Log interno con contexto de request."""
        log_data = {
            'request_id': self.request_id,
            'message': message,
            **kwargs
        }
        getattr(self.logger, level)(json.dumps(sanitize_log_data(log_data)))
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        self._log('critical', message, **kwargs)
