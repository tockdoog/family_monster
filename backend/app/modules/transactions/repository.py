# backend/app/modules/transactions/repository.py
# Consultas a la base de datos de movimientos. TODAS filtran por hogar.

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import Session

from app.modules.members.models import Integrante
from app.modules.transactions.models import LineaMovimiento, Movimiento
from app.shared.pagination import ParametrosPagina


def bloquear_clave_idempotencia(db: Session, hogar_id: uuid.UUID, clave: str) -> None:
    """Candado de transacción por (hogar, clave): serializa solicitudes duplicadas simultáneas.

    Así, si el cliente reenvía la misma operación dos veces a la vez, la segunda espera a que la
    primera termine y entonces encuentra su resultado en lugar de crear un movimiento repetido.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:clave, 0))"),
        {"clave": f"movimiento:{hogar_id}:{clave}"},
    )


def por_clave(db: Session, hogar_id: uuid.UUID, clave: str) -> Movimiento | None:
    """Movimiento ya creado con esa clave de idempotencia en el hogar."""
    return db.execute(
        select(Movimiento).where(
            Movimiento.household_id == hogar_id, Movimiento.clave_idempotencia == clave
        )
    ).scalar_one_or_none()


def integrantes_existentes(
    db: Session, hogar_id: uuid.UUID, ids: Iterable[uuid.UUID]
) -> set[uuid.UUID]:
    """Subconjunto de 'ids' que son integrantes de este hogar."""
    lista = list(ids)
    if not lista:
        return set()
    filas = db.execute(
        select(Integrante.id).where(Integrante.household_id == hogar_id, Integrante.id.in_(lista))
    ).scalars()
    return set(filas)


def crear_movimiento(db: Session, **campos) -> Movimiento:
    """Inserta la cabecera del movimiento."""
    movimiento = Movimiento(**campos)
    db.add(movimiento)
    db.flush()
    return movimiento


def crear_lineas(
    db: Session,
    *,
    movimiento_id: uuid.UUID,
    hogar_id: uuid.UUID,
    lineas: Iterable[tuple[uuid.UUID, Decimal]],
) -> None:
    """Inserta las líneas (cuenta, importe con signo) del movimiento."""
    for cuenta_id, importe in lineas:
        db.add(
            LineaMovimiento(
                transaction_id=movimiento_id,
                household_id=hogar_id,
                account_id=cuenta_id,
                importe=importe,
            )
        )
    db.flush()


def obtener_bloqueando(db: Session, hogar_id: uuid.UUID, movimiento_id: uuid.UUID) -> Movimiento | None:
    """Busca un movimiento SOLO del hogar indicado y lo bloquea para revertirlo sin carreras."""
    return db.execute(
        select(Movimiento)
        .where(Movimiento.id == movimiento_id, Movimiento.household_id == hogar_id)
        .with_for_update()
    ).scalar_one_or_none()


def lineas_de(
    db: Session, movimiento_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, list[LineaMovimiento]]:
    """Líneas agrupadas por movimiento."""
    ids = list(movimiento_ids)
    agrupadas: dict[uuid.UUID, list[LineaMovimiento]] = defaultdict(list)
    if not ids:
        return agrupadas
    filas = db.execute(
        select(LineaMovimiento)
        .where(LineaMovimiento.transaction_id.in_(ids))
        .order_by(LineaMovimiento.importe, LineaMovimiento.id)
    ).scalars()
    for linea in filas:
        agrupadas[linea.transaction_id].append(linea)
    return agrupadas


def listar(
    db: Session,
    hogar_id: uuid.UUID,
    pagina: ParametrosPagina,
    *,
    tipo: str | None,
    estado: str | None,
    cuenta_id: uuid.UUID | None,
    desde: date | None,
    hasta: date | None,
) -> tuple[list[Movimiento], int]:
    """Movimientos del hogar filtrados, del más reciente al más antiguo, con el total."""
    consulta = select(Movimiento).where(Movimiento.household_id == hogar_id)
    if tipo:
        consulta = consulta.where(Movimiento.tipo == tipo)
    if estado:
        consulta = consulta.where(Movimiento.estado == estado)
    if desde:
        consulta = consulta.where(Movimiento.fecha >= desde)
    if hasta:
        consulta = consulta.where(Movimiento.fecha <= hasta)
    if cuenta_id:
        consulta = consulta.where(
            exists().where(
                LineaMovimiento.transaction_id == Movimiento.id,
                LineaMovimiento.account_id == cuenta_id,
            )
        )
    total = db.execute(select(func.count()).select_from(consulta.subquery())).scalar_one()
    filas = db.execute(
        consulta.order_by(Movimiento.fecha.desc(), Movimiento.creado_en.desc(), Movimiento.id)
        .limit(pagina.limite)
        .offset(pagina.desplazamiento)
    ).scalars()
    return list(filas), total


def obtener(db: Session, hogar_id: uuid.UUID, movimiento_id: uuid.UUID) -> Movimiento | None:
    """Busca un movimiento SOLO del hogar indicado (sin bloquearlo)."""
    return db.execute(
        select(Movimiento).where(Movimiento.id == movimiento_id, Movimiento.household_id == hogar_id)
    ).scalar_one_or_none()