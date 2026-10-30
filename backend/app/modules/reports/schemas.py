# backend/app/modules/reports/schemas.py
# Contratos de la API del panel principal y de los informes. Importes en COP enteros.

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.modules.accounts.schemas import CuentaSalida
from app.modules.contributions.schemas import ResumenIntegrante
from app.modules.transactions.schemas import MovimientoSalida
from app.shared.money import PesosSalida


class TotalesPeriodo(BaseModel):
    """Totales de movimientos confirmados del período. Cada concepto se cuenta una sola vez."""

    # Ingresos ordinarios (sueldos, ventas...). No incluye aportes, transferencias ni préstamos.
    ingresos: PesosSalida
    # Dinero que los integrantes entregaron al fondo común.
    aportes: PesosSalida
    # Gastos del hogar: gastos directos y pagos de obligaciones.
    gastos: PesosSalida
    # Cuotas de préstamos pagadas (no son gasto ordinario).
    pagos_de_prestamos: PesosSalida
    # ingresos + aportes - gastos (sin préstamos ni transferencias).
    balance_operativo: PesosSalida


class GastoPorCategoria(BaseModel):
    """Gasto del período en una categoría."""

    categoria_id: uuid.UUID | None
    categoria: str
    importe: PesosSalida


class ResumenObligaciones(BaseModel):
    """Estado actual de las obligaciones."""

    pendientes_cantidad: int
    saldo_pendiente_total: PesosSalida
    vencidas_cantidad: int
    saldo_vencido: PesosSalida


class ResumenPrestamos(BaseModel):
    """Estado actual de los préstamos."""

    activos_cantidad: int
    saldo_pendiente_total: PesosSalida
    cuotas_pendientes_cantidad: int


class Vencimiento(BaseModel):
    """Obligación o cuota próxima a vencer (o ya vencida) con saldo por pagar."""

    tipo: Literal["obligacion", "cuota"]
    referencia_id: uuid.UUID
    descripcion: str
    fecha_vencimiento: date
    saldo: PesosSalida
    vencido: bool


class TableroSalida(BaseModel):
    """Panel principal del hogar."""

    desde: date
    hasta: date
    cuentas: list[CuentaSalida]
    saldo_total: PesosSalida
    totales: TotalesPeriodo
    gastos_por_categoria: list[GastoPorCategoria]
    aportes: list[ResumenIntegrante]
    gastos_sin_distribuir: PesosSalida
    obligaciones: ResumenObligaciones
    prestamos: ResumenPrestamos
    proximos_vencimientos: list[Vencimiento]


class InformeMensual(BaseModel):
    """Informe de un mes: totales, gasto por categoría y todos los movimientos."""

    mes: str
    desde: date
    hasta: date
    totales: TotalesPeriodo
    gastos_por_categoria: list[GastoPorCategoria]
    total_movimientos: int
    # True si el mes tiene más movimientos de los que se incluyen (límite de seguridad).
    truncado: bool
    movimientos: list[MovimientoSalida]