# backend/app/modules/transactions/schemas.py
# Contratos de la API de movimientos. Los importes son pesos colombianos (COP) enteros.

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.money import PesosPositivos, PesosSalida


def _limpiar(valor: str) -> str:
    """Quita espacios sobrantes y rechaza textos vacíos."""
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El texto no puede estar vacío.")
    return limpio


class SolicitudMovimiento(BaseModel):
    """Datos para registrar un ingreso, un gasto o una transferencia.

    - ingreso: requiere cuenta_destino_id.
    - gasto: requiere cuenta_origen_id.
    - transferencia: requiere ambas cuentas y deben ser distintas.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: Literal["ingreso", "gasto", "transferencia"]
    importe: PesosPositivos
    descripcion: str = Field(min_length=1, max_length=500)
    # Si no se envía, se usa la fecha de hoy en Colombia. No puede ser futura.
    fecha: date | None = None
    cuenta_origen_id: uuid.UUID | None = None
    cuenta_destino_id: uuid.UUID | None = None
    # Integrante que pagó con su propio dinero / a quien beneficia (informativos en esta versión).
    pagador_id: uuid.UUID | None = None
    beneficiario_id: uuid.UUID | None = None
    # Solo para ingresos y gastos. Si el gasto tiene una regla de aporte por categoría, se usa esa regla.
    categoria_id: uuid.UUID | None = None

    @field_validator("descripcion")
    @classmethod
    def _limpiar_descripcion(cls, valor: str) -> str:
        """Normaliza la descripción."""
        return _limpiar(valor)


class SolicitudReversion(BaseModel):
    """Motivo obligatorio para revertir un movimiento."""

    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo")
    @classmethod
    def _limpiar_motivo(cls, valor: str) -> str:
        """Normaliza el motivo y exige al menos 5 caracteres reales."""
        limpio = _limpiar(valor)
        if len(limpio) < 5:
            raise ValueError("El motivo es demasiado corto.")
        return limpio


class LineaSalida(BaseModel):
    """Efecto del movimiento en una cuenta: positivo entra dinero, negativo sale."""

    cuenta_id: uuid.UUID
    importe: PesosSalida


class MovimientoSalida(BaseModel):
    """Movimiento con sus líneas."""

    id: uuid.UUID
    tipo: str
    estado: str
    fecha: date
    descripcion: str
    # Dinero movido por el movimiento (lo que entra o lo que sale, el mayor de los dos).
    importe: PesosSalida
    lineas: list[LineaSalida]
    pagador_id: uuid.UUID | None
    beneficiario_id: uuid.UUID | None
    categoria_id: uuid.UUID | None
    registrado_por: uuid.UUID
    reversa_de_id: uuid.UUID | None
    motivo: str | None
    creado_en: datetime