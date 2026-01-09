"""
Schemas y modelos de datos para ModelRouter.
Contratos internos usando Pydantic v2.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    """Mensaje individual en el chat."""

    role: str = Field(..., description="Rol del mensaje: 'user', 'assistant', 'system'")
    content: str = Field(..., description="Contenido del mensaje")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["user", "assistant", "system"]:
            raise ValueError("El rol debe ser 'user', 'assistant' o 'system'")
        return v


class ChatRequest(BaseModel):
    """Request para generación de chat."""

    messages: list[Message] = Field(..., description="Lista de mensajes del chat")
    max_tokens: int = Field(
        default=512, ge=1, le=4096, description="Máximo de tokens a generar"
    )
    temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Temperatura para generación"
    )
    stream: bool = Field(
        default=False, description="Si se debe hacer streaming de la respuesta"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Metadatos adicionales"
    )
    model: Optional[str] = Field(
        default=None, description="Modelo específico a usar (opcional)"
    )
    provider: Optional[str] = Field(
        default=None, description="Proveedor específico a usar (opcional)"
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list[Message]) -> list[Message]:
        if not v:
            raise ValueError("La lista de mensajes no puede estar vacía")
        return v


class ChatResponse(BaseModel):
    """Response de generación no-streaming."""

    text: str = Field(..., description="Texto generado")
    provider: str = Field(..., description="Proveedor que generó la respuesta")
    model: Optional[str] = Field(default=None, description="Modelo usado")
    provider_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadatos del proveedor (tokens, latencia, etc.)",
    )


class HealthResponse(BaseModel):
    """Response del endpoint de salud."""

    status: str = Field(..., description="Estado del servicio")
    version: str = Field(..., description="Versión de la aplicación")
    providers: dict[str, str] = Field(..., description="Estado de cada proveedor")


class ErrorResponse(BaseModel):
    """Response de error estándar."""

    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje descriptivo del error")
    request_id: Optional[str] = Field(
        default=None, description="ID de la request para trazabilidad"
    )


class ProviderError(Exception):
    """Error específico de proveedor con información de retriabilidad."""

    def __init__(
        self,
        provider: str,
        code: str,
        message: str,
        retriable: bool = False,
        original_error: Optional[Exception] = None,
    ):
        self.provider = provider
        self.code = code
        self.message = message
        self.retriable = retriable
        self.original_error = original_error
        super().__init__(f"[{provider}] {code}: {message}")
