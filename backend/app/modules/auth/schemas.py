# backend/app/modules/auth/schemas.py
# Contratos de entrada y salida de la autenticación (lo que recibe y devuelve la API).

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SolicitudLogin(BaseModel):
    """Datos para iniciar sesión."""

    # Rechaza campos desconocidos para no aceptar datos inesperados.
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    contrasena: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        """El correo siempre se compara en minúsculas."""
        return valor.strip().lower()


class UsuarioSalida(BaseModel):
    """Datos públicos del usuario autenticado (nunca incluye el hash)."""

    id: uuid.UUID
    email: str
    nombre_completo: str


class HogarResumen(BaseModel):
    """Identificación mínima del hogar."""

    id: uuid.UUID
    nombre: str


class SesionSalida(BaseModel):
    """Estado de la sesión: quién es el usuario, su hogar, su rol y sus permisos."""

    usuario: UsuarioSalida
    hogar: HogarResumen
    rol: str
    # Solo informativo para la interfaz: el backend valida los permisos en cada petición.
    permisos: list[str]