# backend/app/modules/accounts/repository.py
# Consultas a la base de datos de cuentas. Todas filtran por hogar.

import uuid
from collections.abc import Iterable
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.accounts.models import Cuenta
from app.modules.transactions.models import ESTADOS_CON_EFECTO, LineaMovimiento, Movimiento


def _consulta_saldos():
    """Consulta base: (cuenta, saldo actual) = saldo inicial + suma de líneas con efecto."""
    suma_lineas = (
        select(
            LineaMovimiento.account_id.label("cuenta_id"),
            func.coalesce(func.sum(LineaMovimiento.importe), 0).label("suma"),
        )
        .join(Movimiento, Movimiento.id == LineaMovimiento.transaction_id)
        .where(Movimiento.estado.in_(ESTADOS_CON_EFECTO))
        .group_by(LineaMovimiento.account_id)
        .subquery()
    )
    return (
        select(Cuenta, Cuenta.saldo_inicial + func.coalesce(suma_lineas.c.suma, 0))
        .outerjoin(suma_lineas, suma_lineas.c.cuenta_id == Cuenta.id)
    )


def listar_con_saldo(db: Session, hogar_id: uuid.UUID) -> list[tuple[Cuenta, Decimal]]:
    """Cuentas del hogar con su saldo derivado, ordenadas por nombre."""
    filas = db.execute(
        _consulta_saldos().where(Cuenta.household_id == hogar_id).order_by(Cuenta.nombre)
    ).all()
    return [(fila[0], fila[1]) for fila in filas]


def obtener_con_saldo(
    db: Session, hogar_id: uuid.UUID, cuenta_id: uuid.UUID
) -> tuple[Cuenta, Decimal] | None:
    """Una cuenta del hogar con su saldo derivado, o None si no existe en ese hogar."""
    fila = db.execute(
        _consulta_saldos().where(Cuenta.household_id == hogar_id, Cuenta.id == cuenta_id)
    ).first()
    return None if fila is None else (fila[0], fila[1])


def saldos_de(db: Session, hogar_id: uuid.UUID, cuenta_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Decimal]:
    """Saldo derivado de varias cuentas del hogar."""
    ids = list(cuenta_ids)
    if not ids:
        return {}
    filas = db.execute(
        _consulta_saldos().where(Cuenta.household_id == hogar_id, Cuenta.id.in_(ids))
    ).all()
    return {fila[0].id: fila[1] for fila in filas}


def bloquear_cuentas(
    db: Session, hogar_id: uuid.UUID, cuenta_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, Cuenta]:
    """Bloquea las cuentas (FOR UPDATE) para que dos movimientos simultáneos no gasten el mismo saldo.

    Se bloquean siempre ordenadas por id: así dos operaciones concurrentes nunca se bloquean en cruz.
    """
    ids = list(cuenta_ids)
    if not ids:
        return {}
    filas = db.execute(
        select(Cuenta)
        .where(Cuenta.household_id == hogar_id, Cuenta.id.in_(ids))
        .order_by(Cuenta.id)
        .with_for_update()
    ).scalars()
    return {cuenta.id: cuenta for cuenta in filas}


def crear_cuenta(
    db: Session,
    *,
    household_id: uuid.UUID,
    nombre: str,
    tipo: str,
    saldo_inicial: Decimal,
    propietario_id: uuid.UUID | None,
) -> Cuenta:
    """Inserta una cuenta nueva."""
    cuenta = Cuenta(
        household_id=household_id,
        nombre=nombre,
        tipo=tipo,
        saldo_inicial=saldo_inicial,
        propietario_id=propietario_id,
    )
    db.add(cuenta)
    db.flush()
    return cuenta