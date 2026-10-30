# backend/app/modules/households/schemas.py
# Contratos de la API del hogar y de la instalación inicial.

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HogarSalida(BaseModel):
    """Datos del hogar actual."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    moneda: str
    zona_horaria: str


class SolicitudInstalacion(BaseModel):
    """Datos para crear el primer hogar y su administrador."""

    model_config = ConfigDict(extra="forbid")

    nombre_hogar: str = Field(min_length=1, max_length=120)
    nombre_completo: str = Field(min_length=1, max_length=120)
    email: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)

    @field_validator("nombre_hogar", "nombre_completo")
    @classmethod
    def _limpiar_texto(cls, valor: str) -> str:
        """Quita espacios sobrantes y rechaza textos vacíos."""
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El texto no puede estar vacío.")
        return limpio

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        """El correo siempre se guarda en minúsculas."""
        return valor.strip().lower()