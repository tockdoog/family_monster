# backend/app/modules/categories/schemas.py
# Contratos de la API de categorías.

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _limpiar_nombre(valor: str) -> str:
    """Quita espacios sobrantes y rechaza nombres vacíos."""
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El nombre no puede estar vacío.")
    return limpio


class CategoriaSalida(BaseModel):
    """Categoría tal como la ve la interfaz."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    activa: bool


class SolicitudCrearCategoria(BaseModel):
    """Datos para crear una categoría."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=60)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str) -> str:
        """Normaliza el nombre."""
        return _limpiar_nombre(valor)


class SolicitudActualizarCategoria(BaseModel):
    """Cambios permitidos: renombrar y/o activar o desactivar."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    activa: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str | None) -> str | None:
        """Normaliza el nombre si viene."""
        return None if valor is None else _limpiar_nombre(valor)

    @model_validator(mode="after")
    def _al_menos_un_cambio(self) -> "SolicitudActualizarCategoria":
        """Una actualización vacía no tiene sentido."""
        if self.nombre is None and self.activa is None:
            raise ValueError("Debe indicar al menos un cambio.")
        return self