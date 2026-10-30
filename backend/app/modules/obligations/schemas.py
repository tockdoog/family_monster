# backend/app/modules/obligations/schemas.py
# Contratos de la API de obligaciones. Los importes son pesos colombianos (COP) enteros.

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.money import PesosPositivos, PesosSalida


def _limpiar(valor: str) -> str:
    """Quita espacios sobrantes y rechaza textos vacíos."""
    limpio = valor.strip()
    if not limpio:
        raise ValueError("El texto no puede estar vacío.")
    return limpio


class SolicitudCrearObligacion(BaseModel):
    """Datos para registrar una factura, servicio, deuda u otra obligación."""

    model_config = ConfigDict(extra="forbid")

    descripcion: str = Field(min_length=1, max_length=300)
    categoria_id: uuid.UUID
    importe_original: PesosPositivos
    fecha_vencimiento: date
    acreedor: str = Field(min_length=1, max_length=120)
    # Si no se indica, se usa la fecha de hoy en Colombia.
    fecha_creacion: date | None = None
    responsable_id: uuid.UUID | None = None

    @field_validator("descripcion", "acreedor")
    @classmethod
    def _textos(cls, valor: str) -> str:
        """Normaliza los textos."""
        return _limpiar(valor)


class SolicitudPagoObligacion(BaseModel):
    """Pago total o parcial de una obligación desde una cuenta."""

    model_config = ConfigDict(extra="forbid")

    importe: PesosPositivos
    # Si es la cuenta personal de un integrante, queda registrado como pago directo por cuenta del hogar.
    cuenta_origen_id: uuid.UUID
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1, max_length=500)


class SolicitudAnularObligacion(BaseModel):
    """Motivo obligatorio para anular una obligación."""

    model_config = ConfigDict(extra="forbid")

    motivo: str = Field(min_length=5, max_length=500)

    @field_validator("motivo")
    @classmethod
    def _motivo(cls, valor: str) -> str:
        """Normaliza el motivo y exige al menos 5 caracteres reales."""
        limpio = _limpiar(valor)
        if len(limpio) < 5:
            raise ValueError("El motivo es demasiado corto.")
        return limpio


EstadoObligacion = Literal["pendiente", "parcialmente_pagada", "pagada", "vencida", "anulada"]


class PagoObligacionSalida(BaseModel):
    """Un pago de la obligación, con el estado de su movimiento (revertido o confirmado)."""

    movimiento_id: uuid.UUID
    fecha: date
    importe: PesosSalida
    estado_movimiento: str


class ObligacionSalida(BaseModel):
    """Obligación con su saldo y estado calculados desde los pagos confirmados."""

    id: uuid.UUID
    descripcion: str
    categoria_id: uuid.UUID
    importe_original: PesosSalida
    pagado: PesosSalida
    saldo_pendiente: PesosSalida
    estado: EstadoObligacion
    fecha_creacion: date
    fecha_vencimiento: date
    acreedor: str
    responsable_id: uuid.UUID | None
    motivo_anulacion: str | None


class ObligacionDetalle(ObligacionSalida):
    """Obligación con el historial de sus pagos."""

    pagos: list[PagoObligacionSalida]


class PagoRegistradoSalida(BaseModel):
    """Resultado de pagar: el pago realizado y la obligación actualizada."""

    pago: PagoObligacionSalida
    obligacion: ObligacionSalida