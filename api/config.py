"""
Configuración de la aplicación usando Pydantic Settings.
Lee variables de entorno y archivo .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración global de la aplicación."""

    # Aplicación
    app_env: str = "development"
    app_name: str = "ModelRouter"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Claves API
    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # URLs base de proveedores
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Timeouts (segundos)
    provider_timeout: float = 30.0
    first_chunk_timeout: float = 3.0
    max_operation_timeout: float = 120.0

    # Backoff y reintentos
    max_retries: int = 2
    backoff_base_seconds: int = 5
    backoff_max_seconds: int = 300

    # Rate limiting
    rate_limit_requests_per_minute: int = 60
    max_concurrent_streams: int = 10

    # Autenticación
    api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Instancia global de configuración
settings = Settings()
