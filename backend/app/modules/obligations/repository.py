# backend/app/modules/obligations/repository.py
# Consultas a la base de datos de obligaciones y sus pagos. Todas filtran por hogar.

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.obligations.models import Obligacion, PagoObligacion
from app.modules.transactions.models import EstadoMovimiento, Movimiento

# Estado de un movimiento vigente: los pagos de movimientos revertidos no cuentan como pagado.
_CONFIRMADA = EstadoMovimiento.CONFIRMADA.value


def crear(db: Session, **campos) -> Obligacion:
    """Inserta una obligación."""
    obligacion = Obligacion(**campos)
    db.add(obligacion)
    db.flush()
    return obligacion


def obtener(
    db: Session, hogar_id: uuid.UUID, obligacion_id: uuid.UUID, *, bloquear: bool = False
) -> Obligacion | None:
    """Busca una obligación SOLO del hogar indicado; opcionalmente la bloquea para pagarla sin carreras."""
    consulta = select(Obligacion).where(
        Obligacion.id == obligacion_id, Obligacion.household_id == hogar_id
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.execute(consulta).scalar_one_or_none()


def pagado_de(db: Session, obligacion_id: uuid.UUID) -> Decimal:
    """Total pagado de una obligación (solo pagos cuyo movimiento sigue confirmado)."""
    return db.execute(
        select(func.coalesce(func.sum(PagoObligacion.importe), 0))
        .join(Movimiento, Movimiento.id == PagoObligacion.transaction_id)
        .where(PagoObligacion.obligation_id == obligacion_id, Movimiento.estado == _CONFIRMADA)
    ).scalar_one()


def listar_con_pagado(db: Session, hogar_id: uuid.UUID) -> list[tuple[Obligacion, Decimal]]:
    """Todas las obligaciones del hogar con lo pagado de cada una (por vencimiento ascendente)."""
    pagado = (
        select(
            PagoObligacion.obligation_id.label("obligacion_id"),
            func.sum(PagoObligacion.importe).label("pagado"),
        )
        .join(Movimiento, Movimiento.id == PagoObligacion.transaction_id)
        .where(Movimiento.estado == _CONFIRMADA)
        .group_by(PagoObligacion.obligation_id)
        .subquery()
    )
    filas = db.execute(
        select(Obligacion, func.coalesce(pagado.c.pagado, 0))
        .outerjoin(pagado, pagado.c.obligacion_id == Obligacion.id)
        .where(Obligacion.household_id == hogar_id)
        .order_by(Obligacion.fecha_vencimiento, Obligacion.creado_en, Obligacion.id)
    ).all()
    return [(fila[0], fila[1]) for fila in filas]


def crear_pago(
    db: Session,
    *,
    hogar_id: uuid.UUID,
    obligacion_id: uuid.UUID,
    movimiento_id: uuid.UUID,
    importe: Decimal,
) -> PagoObligacion:
    """Vincula un movimiento real con la obligación que paga."""
    pago = PagoObligacion(
        household_id=hogar_id, obligation_id=obligacion_id, transaction_id=movimiento_id, importe=importe
    )
    db.add(pago)
    db.flush()
    return pago


def pago_por_movimiento(db: Session, movimiento_id: uuid.UUID) -> PagoObligacion:
    """Pago de obligación vinculado a un movimiento ya registrado.

    Se usa cuando el cliente repite un pago con la misma clave de idempotencia: el movimiento original
    ya existe (y ya pertenece al hogar, porque se halló por su clave) y se devuelve su pago sin cobrar de nuevo.
    Hay como máximo uno por movimiento (restricción única en la base de datos).
    """
    return db.execute(
        select(PagoObligacion).where(PagoObligacion.transaction_id == movimiento_id)
    ).scalar_one()


def pagos_de(db: Session, obligacion_id: uuid.UUID) -> list[tuple[PagoObligacion, Movimiento]]:
    """Pagos de una obligación con su movimiento (incluye los revertidos, marcados por su estado)."""
    filas = db.execute(
        select(PagoObligacion, Movimiento)
        .join(Movimiento, Movimiento.id == PagoObligacion.transaction_id)
        .where(PagoObligacion.obligation_id == obligacion_id)
        .order_by(Movimiento.fecha, Movimiento.creado_en)
    ).all()
    return [(fila[0], fila[1]) for fila in filas]