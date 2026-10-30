# backend/app/modules/reports/repository.py
# Consultas de agregación para informes. Solo cuentan movimientos CONFIRMADOS y filtran por hogar.

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.transactions.models import (
    EstadoMovimiento,
    LineaMovimiento,
    Movimiento,
    TIPOS_GASTO_HOGAR,
)


def _base(hogar_id: uuid.UUID, desde: date, hasta: date):
    """Condiciones comunes: del hogar, confirmado y dentro del período."""
    return (
        Movimiento.household_id == hogar_id,
        Movimiento.estado == EstadoMovimiento.CONFIRMADA.value,
        Movimiento.fecha >= desde,
        Movimiento.fecha <= hasta,
    )


def sumas_por_tipo(
    db: Session, hogar_id: uuid.UUID, desde: date, hasta: date
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Suma de líneas positivas (entradas) y de líneas negativas en positivo (salidas), por tipo."""
    def _consulta(signo_positivo: bool) -> dict[str, Decimal]:
        importe = LineaMovimiento.importe if signo_positivo else -LineaMovimiento.importe
        filtro = LineaMovimiento.importe > 0 if signo_positivo else LineaMovimiento.importe < 0
        filas = db.execute(
            select(Movimiento.tipo, func.sum(importe))
            .join(LineaMovimiento, LineaMovimiento.transaction_id == Movimiento.id)
            .where(*_base(hogar_id, desde, hasta), filtro)
            .group_by(Movimiento.tipo)
        ).all()
        return {fila[0]: fila[1] for fila in filas}

    return _consulta(True), _consulta(False)


def gastos_por_categoria(
    db: Session, hogar_id: uuid.UUID, desde: date, hasta: date
) -> list[tuple[uuid.UUID | None, Decimal]]:
    """Gasto del hogar agrupado por categoría (la categoría nula agrupa lo no clasificado)."""
    filas = db.execute(
        select(Movimiento.categoria_id, func.sum(-LineaMovimiento.importe))
        .join(LineaMovimiento, LineaMovimiento.transaction_id == Movimiento.id)
        .where(*_base(hogar_id, desde, hasta), Movimiento.tipo.in_(TIPOS_GASTO_HOGAR), LineaMovimiento.importe < 0)
        .group_by(Movimiento.categoria_id)
        .order_by(func.sum(-LineaMovimiento.importe).desc())
    ).all()
    return [(fila[0], fila[1]) for fila in filas]