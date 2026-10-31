# backend/app/modules/loans/repository.py
# Consultas a la base de datos de préstamos, cuotas y pagos. Todas filtran por hogar.

import uuid
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.modules.loans.models import Cuota, PagoCuota, Prestamo
from app.modules.transactions.models import EstadoMovimiento, Movimiento

# Estado de un movimiento vigente: los pagos de movimientos revertidos no cuentan como pagado.
_CONFIRMADA = EstadoMovimiento.CONFIRMADA.value


def crear_prestamo(db: Session, **campos) -> Prestamo:
    """Inserta un préstamo."""
    prestamo = Prestamo(**campos)
    db.add(prestamo)
    db.flush()
    return prestamo


def prestamo_por_desembolso(db: Session, movimiento_id: uuid.UUID) -> Prestamo:
    """Préstamo creado por un desembolso ya registrado.

    Se usa cuando el cliente repite la creación con la misma clave de idempotencia: el movimiento de
    desembolso original ya existe y se devuelve su préstamo sin crear otro.
    """
    return db.execute(
        select(Prestamo).where(Prestamo.desembolso_transaction_id == movimiento_id)
    ).scalar_one()


def crear_cuotas(
    db: Session,
    *,
    prestamo_id: uuid.UUID,
    hogar_id: uuid.UUID,
    cuotas: Iterable[tuple[int, date, Decimal]],
) -> list[Cuota]:
    """Inserta las cuotas (número, vencimiento, importe) de un préstamo."""
    creadas = [
        Cuota(loan_id=prestamo_id, household_id=hogar_id, numero=n, fecha_vencimiento=f, importe=i)
        for n, f, i in cuotas
    ]
    db.add_all(creadas)
    db.flush()
    return creadas


def obtener(
    db: Session, hogar_id: uuid.UUID, prestamo_id: uuid.UUID, *, bloquear: bool = False
) -> Prestamo | None:
    """Busca un préstamo SOLO del hogar indicado; opcionalmente lo bloquea para pagarlo sin carreras."""
    consulta = select(Prestamo).where(Prestamo.id == prestamo_id, Prestamo.household_id == hogar_id)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.execute(consulta).scalar_one_or_none()


def listar(db: Session, hogar_id: uuid.UUID) -> list[Prestamo]:
    """Préstamos del hogar, del más reciente al más antiguo."""
    return list(
        db.execute(
            select(Prestamo)
            .where(Prestamo.household_id == hogar_id)
            .order_by(Prestamo.fecha.desc(), Prestamo.creado_en.desc(), Prestamo.id)
        ).scalars()
    )


def cuotas_de(db: Session, prestamo_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[Cuota]]:
    """Cuotas agrupadas por préstamo, ordenadas por número."""
    ids = list(prestamo_ids)
    agrupadas: dict[uuid.UUID, list[Cuota]] = {i: [] for i in ids}
    if not ids:
        return agrupadas
    for cuota in db.execute(
        select(Cuota).where(Cuota.loan_id.in_(ids)).order_by(Cuota.loan_id, Cuota.numero)
    ).scalars():
        agrupadas[cuota.loan_id].append(cuota)
    return agrupadas


def pagado_por_cuota(db: Session, cuota_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    """Lo pagado de cada cuota (solo pagos cuyo movimiento sigue confirmado)."""
    ids = list(cuota_ids)
    if not ids:
        return {}
    filas = db.execute(
        select(PagoCuota.installment_id, func.sum(PagoCuota.importe))
        .join(Movimiento, Movimiento.id == PagoCuota.transaction_id)
        .where(PagoCuota.installment_id.in_(ids), Movimiento.estado == _CONFIRMADA)
        .group_by(PagoCuota.installment_id)
    ).all()
    return {fila[0]: fila[1] for fila in filas}


def estados_de_movimientos(db: Session, movimiento_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Estado (confirmada o revertida) de cada movimiento indicado."""
    ids = list(movimiento_ids)
    if not ids:
        return {}
    return {
        fila[0]: fila[1]
        for fila in db.execute(
            select(Movimiento.id, Movimiento.estado).where(Movimiento.id.in_(ids))
        ).all()
    }


def crear_pago(
    db: Session, *, hogar_id: uuid.UUID, cuota_id: uuid.UUID, movimiento_id: uuid.UUID, importe: Decimal
) -> PagoCuota:
    """Vincula un movimiento real con la cuota que paga."""
    pago = PagoCuota(
        household_id=hogar_id, installment_id=cuota_id, transaction_id=movimiento_id, importe=importe
    )
    db.add(pago)
    db.flush()
    return pago


def pago_por_movimiento(db: Session, movimiento_id: uuid.UUID) -> tuple[PagoCuota, Cuota]:
    """Pago de cuota (y la cuota que paga) vinculado a un movimiento ya registrado.

    Se usa cuando el cliente repite un pago con la misma clave de idempotencia: el movimiento original
    ya existe y se devuelve su pago sin cobrar de nuevo.
    """
    fila = db.execute(
        select(PagoCuota, Cuota)
        .join(Cuota, Cuota.id == PagoCuota.installment_id)
        .where(PagoCuota.transaction_id == movimiento_id)
    ).one()
    return fila[0], fila[1]


def tiene_pagos_confirmados(db: Session, desembolso_movimiento_id: uuid.UUID) -> bool:
    """Indica si el préstamo asociado a ese desembolso ya tiene pagos de cuotas confirmados."""
    return db.execute(
        select(
            exists()
            .where(Prestamo.desembolso_transaction_id == desembolso_movimiento_id)
            .where(Cuota.loan_id == Prestamo.id)
            .where(PagoCuota.installment_id == Cuota.id)
            .where(PagoCuota.transaction_id == Movimiento.id)
            .where(Movimiento.estado == _CONFIRMADA)
        )
    ).scalar_one()


def pagos_de_prestamo(db: Session, prestamo_id: uuid.UUID) -> list[tuple[PagoCuota, int, Movimiento]]:
    """Pagos de un préstamo: (pago, número de cuota, movimiento), incluidos los revertidos."""
    filas = db.execute(
        select(PagoCuota, Cuota.numero, Movimiento)
        .join(Cuota, Cuota.id == PagoCuota.installment_id)
        .join(Movimiento, Movimiento.id == PagoCuota.transaction_id)
        .where(Cuota.loan_id == prestamo_id)
        .order_by(Movimiento.fecha, Movimiento.creado_en)
    ).all()
    return [(fila[0], fila[1], fila[2]) for fila in filas]