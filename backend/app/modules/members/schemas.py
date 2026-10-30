# backend/app/modules/members/schemas.py
# Contratos de la API de integrantes.

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class IntegranteSalida(BaseModel):
    """Integrante del hogar tal como lo ve la interfaz."""

    id: uuid.UUID
    nombre: str
    activo: bool
    # Indica si la persona puede entrar a la aplicación.
    tiene_acceso: bool
    # Rol de acceso, o None si el integrante no tiene acceso.
    rol: str | None


class SolicitudCrearIntegrante(BaseModel):
    """Datos para registrar un integrante (con o sin acceso a la app)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)

    @field_validator("nombre")
    @classmethod
    def _limpiar_nombre(cls, valor: str) -> str:
        """Quita espacios sobrantes y rechaza nombres vacíos."""
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre no puede estar vacío.")
        return limpio


class SolicitudOtorgarAcceso(BaseModel):
    """Datos para darle acceso a la aplicación a un integrante existente."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)
    rol: Literal["admin", "miembro"] = "miembro"

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        """El correo siempre se guarda en minúsculas."""
        return valor.strip().lower()