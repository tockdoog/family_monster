# backend/app/modules/contributions/schemas.py
# Contratos de la API de reglas de aporte, aportes, reembolsos y resumen. Importes en COP enteros.

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.money import PesosPositivos, PesosSalida, validar_pesos_enteros

TipoItem = Literal["porcentaje", "parte", "fijo"]


class ItemReglaSolicitud(BaseModel):
    """Parte de un integrante en una regla.

    - porcentaje: 'valor' entre 0,01 y 100 (porcentaje del gasto que queda después de los fijos).
    - parte: parte igual con los demás integrantes 'parte'; no lleva valor.
    - fijo: 'valor' en pesos COP que ese integrante paga siempre.
    """

    model_config = ConfigDict(extra="forbid")

    integrante_id: uuid.UUID
    tipo: TipoItem
    valor: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)

    @model_validator(mode="after")
    def _validar_valor(self) -> "ItemReglaSolicitud":
        """Cada tipo exige (o prohíbe) un valor concreto."""
        if self.tipo == "parte":
            if self.valor is not None:
                raise ValueError("Una parte igual no lleva valor.")
            self.valor = Decimal(1)
        elif self.valor is None or self.valor <= 0:
            raise ValueError("El valor debe ser mayor que cero.")
        elif self.tipo == "porcentaje" and self.valor > 100:
            raise ValueError("Un porcentaje no puede superar 100.")
        elif self.tipo == "fijo":
            self.valor = validar_pesos_enteros(self.valor)
        return self


class SolicitudRegla(BaseModel):
    """Datos para crear una regla de reparto con vigencia."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=120)
    # Sin categoría = regla general del hogar; con categoría = solo para gastos de esa categoría.
    categoria_id: uuid.UUID | None = None
    vigente_desde: date
    items: list[ItemReglaSolicitud] = Field(min_length=1, max_length=50)

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, valor: str) -> str:
        """Normaliza el nombre."""
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El nombre no puede estar vacío.")
        return limpio


class ItemReglaSalida(BaseModel):
    """Parte de un integrante en una regla guardada."""

    integrante_id: uuid.UUID
    tipo: str
    valor: Decimal


class ReglaSalida(BaseModel):
    """Regla con su vigencia y sus partes."""

    id: uuid.UUID
    nombre: str
    categoria_id: uuid.UUID | None
    vigente_desde: date
    vigente_hasta: date | None
    items: list[ItemReglaSalida]


class ParteSalida(BaseModel):
    """Lo que le correspondió pagar a un integrante de un gasto concreto (foto histórica)."""

    integrante_id: uuid.UUID
    regla_id: uuid.UUID
    tipo: str
    valor: Decimal
    importe: PesosSalida


class SolicitudAporte(BaseModel):
    """Dinero que un integrante entrega al fondo común."""

    model_config = ConfigDict(extra="forbid")

    integrante_id: uuid.UUID
    importe: PesosPositivos
    # Cuenta del fondo común que recibe el dinero.
    cuenta_destino_id: uuid.UUID
    # Solo si el dinero sale de la cuenta personal del propio integrante; si no, entra desde fuera del sistema.
    cuenta_origen_id: uuid.UUID | None = None
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1, max_length=500)


class SolicitudReembolso(BaseModel):
    """Devolución del fondo común a un integrante que pagó gastos con su propio dinero."""

    model_config = ConfigDict(extra="forbid")

    integrante_id: uuid.UUID
    importe: PesosPositivos
    cuenta_origen_id: uuid.UUID
    cuenta_destino_id: uuid.UUID
    fecha: date | None = None
    descripcion: str | None = Field(default=None, min_length=1, max_length=500)


class ResumenIntegrante(BaseModel):
    """Estado de aportes de un integrante en el período."""

    integrante_id: uuid.UUID
    nombre: str
    # Lo que le correspondía pagar de los gastos repartidos.
    obligacion_esperada: PesosSalida
    aportes: PesosSalida
    pagos_directos: PesosSalida
    reembolsos: PesosSalida
    # aportes + pagos directos - reembolsos: lo que realmente puso.
    aportado_neto: PesosSalida
    # Positivo = saldo a favor; negativo = le falta aportar.
    saldo: PesosSalida
    estado: Literal["al_dia", "pendiente"]
    # Dinero que el hogar le debe por pagos directos aún no reembolsados (histórico, no solo del período).
    reembolso_pendiente: PesosSalida


class ResumenAportes(BaseModel):
    """Resumen de aportes esperados y reales de todos los integrantes."""

    desde: date
    hasta: date
    integrantes: list[ResumenIntegrante]
    total_esperado: PesosSalida
    total_aportado_neto: PesosSalida
    # Gastos del período a los que no se les aplicó ninguna regla (no cuentan en lo esperado).
    gastos_sin_distribuir: PesosSalida