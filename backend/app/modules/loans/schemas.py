# backend/app/modules/loans/schemas.py
# Contratos de la API de préstamos y cuotas. Los importes son pesos colombianos (COP) enteros.

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.money import PesosPositivos, PesosSalida

TipoPrestamo = Literal["entre_integrantes", "al_hogar", "del_hogar"]
EstadoPrestamo = Literal["activo", "pagado", "anulado"]
EstadoCuota = Literal["pendiente", "parcialmente_pagada", "pagada", "vencida"]


class SolicitudPrestamo(BaseModel):
    """Datos para crear un préstamo. Al crearlo se registra también el desembolso del dinero.

    - entre_integrantes: prestamista y prestatario son integrantes; el dinero sale de la cuenta
      personal del prestamista y entra en la del prestatario (ambas obligatorias).
    - al_hogar: el hogar recibe (de un integrante o de un tercero); requiere cuenta_destino del fondo común.
    - del_hogar: el hogar presta (a un integrante o a un tercero); requiere cuenta_origen del fondo común.
    """

    model_config = ConfigDict(extra="forbid")

    tipo: TipoPrestamo
    importe: PesosPositivos
    numero_cuotas: int = Field(ge=1, le=360)
    prestamista_integrante_id: uuid.UUID | None = None
    prestatario_integrante_id: uuid.UUID | None = None
    # Nombre del tercero (banco, persona externa) cuando no es un integrante.
    contraparte_nombre: str | None = Field(default=None, min_length=1, max_length=120)
    # Total a devolver, incluidos intereses. Si no se indica, es igual al importe prestado.
    total_a_pagar: PesosPositivos | None = None
    fecha: date | None = None
    primer_vencimiento: date | None = None
    condiciones: str | None = Field(default=None, min_length=1, max_length=1000)
    cuenta_origen_id: uuid.UUID | None = None
    cuenta_destino_id: uuid.UUID | None = None

    @field_validator("contraparte_nombre")
    @classmethod
    def _contraparte(cls, valor: str | None) -> str | None:
        """Normaliza el nombre del tercero."""
        if valor is None:
            return None
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre no puede estar vacío.")
        return limpio


class SolicitudPagoCuota(BaseModel):
    """Pago total o parcial de una cuota.

    - entre_integrantes: cuenta_origen = cuenta personal del prestatario y cuenta_destino = la del prestamista.
    - al_hogar: cuenta_origen del fondo común (el hogar paga); sin cuenta_destino.
    - del_hogar: cuenta_destino del fondo común (el hogar cobra); sin cuenta_origen.
    """

    model_config = ConfigDict(extra="forbid")

    cuota_numero: int = Field(ge=1)
    importe: PesosPositivos
    cuenta_origen_id: uuid.UUID | None = None
    cuenta_destino_id: uuid.UUID | None = None
    fecha: date | None = None


class CuotaSalida(BaseModel):
    """Cuota con lo pagado y su estado, derivados de los pagos confirmados."""

    id: uuid.UUID
    numero: int
    fecha_vencimiento: date
    importe: PesosSalida
    pagado: PesosSalida
    saldo: PesosSalida
    estado: EstadoCuota


class PagoCuotaSalida(BaseModel):
    """Un pago de cuota, con el estado de su movimiento."""

    movimiento_id: uuid.UUID
    cuota_numero: int
    fecha: date
    importe: PesosSalida
    estado_movimiento: str


class PrestamoSalida(BaseModel):
    """Préstamo con su saldo, estado y cuotas."""

    id: uuid.UUID
    tipo: str
    prestamista_integrante_id: uuid.UUID | None
    prestatario_integrante_id: uuid.UUID | None
    contraparte_nombre: str | None
    fecha: date
    importe: PesosSalida
    total_a_pagar: PesosSalida
    pagado: PesosSalida
    saldo_pendiente: PesosSalida
    estado: EstadoPrestamo
    condiciones: str | None
    desembolso_movimiento_id: uuid.UUID
    cuotas: list[CuotaSalida]


class PrestamoDetalle(PrestamoSalida):
    """Préstamo con el historial de pagos."""

    pagos: list[PagoCuotaSalida]


class PagoCuotaRegistradoSalida(BaseModel):
    """Resultado de pagar una cuota: el pago y el préstamo actualizado."""

    pago: PagoCuotaSalida
    prestamo: PrestamoSalida