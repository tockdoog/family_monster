# backend/app/modules/accounts/schemas.py
# Contratos de la API de cuentas. Los importes son pesos colombianos (COP) enteros.

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.money import PesosNoNegativos, PesosSalida


class SolicitudCrearCuenta(BaseModel):
    """Datos para crear una cuenta o fondo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    tipo: Literal["efectivo", "banco", "personal", "otra"]
    # Dinero con el que la cuenta ya cuenta al registrarla (no se puede editar después).
    saldo_inicial: PesosNoNegativos = 0  # type: ignore[assignment]
    # Obligatorio solo en cuentas personales.
    propietario_id: uuid.UUID | None = None

    @field_validator("nombre")
    @classmethod
    def _limpiar_nombre(cls, valor: str) -> str:
        """Quita espacios sobrantes y rechaza nombres vacíos."""
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre no puede estar vacío.")
        return limpio


class CuentaSalida(BaseModel):
    """Cuenta con su saldo actual calculado a partir de los movimientos."""

    id: uuid.UUID
    nombre: str
    tipo: str
    # True para fondo común (efectivo, banco, otra); False para fondos personales.
    es_fondo_comun: bool
    propietario_id: uuid.UUID | None
    saldo_inicial: PesosSalida
    saldo_actual: PesosSalida
    activa: bool