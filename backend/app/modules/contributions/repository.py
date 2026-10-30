# backend/app/modules/contributions/repository.py
# Consultas a la base de datos de reglas, repartos y resúmenes de aportes. Todas filtran por hogar.

import uuid
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.modules.accounts.models import Cuenta
from app.modules.contributions.models import ItemReglaAporte, ParteAporte, ReglaAporte
from app.modules.transactions.models import (
    EstadoMovimiento,
    LineaMovimiento,
    Movimiento,
    TIPOS_GASTO_HOGAR,
    TipoMovimiento,
)

_CONFIRMADA = EstadoMovimiento.CONFIRMADA.value


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------
def regla_vigente(
    db: Session, hogar_id: uuid.UUID, categoria_id: uuid.UUID | None, fecha: date
) -> ReglaAporte | None:
    """Regla del alcance indicado (una categoría o la general) vigente en la fecha dada."""
    filtro_categoria = (
        ReglaAporte.categoria_id.is_(None) if categoria_id is None else ReglaAporte.categoria_id == categoria_id
    )
    return db.execute(
        select(ReglaAporte)
        .where(
            ReglaAporte.household_id == hogar_id,
            filtro_categoria,
            ReglaAporte.vigente_desde <= fecha,
            (ReglaAporte.vigente_hasta.is_(None)) | (ReglaAporte.vigente_hasta >= fecha),
        )
        .order_by(ReglaAporte.vigente_desde.desc())
        .limit(1)
    ).scalar_one_or_none()


def regla_abierta_del_alcance(
    db: Session, hogar_id: uuid.UUID, categoria_id: uuid.UUID | None
) -> ReglaAporte | None:
    """Regla más reciente del alcance que todavía no tiene fecha de fin (bloqueada para actualizarla)."""
    filtro_categoria = (
        ReglaAporte.categoria_id.is_(None) if categoria_id is None else ReglaAporte.categoria_id == categoria_id
    )
    return db.execute(
        select(ReglaAporte)
        .where(ReglaAporte.household_id == hogar_id, filtro_categoria, ReglaAporte.vigente_hasta.is_(None))
        .order_by(ReglaAporte.vigente_desde.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()


def items_de(db: Session, regla_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, list[ItemReglaAporte]]:
    """Ítems agrupados por regla, en un orden estable."""
    ids = list(regla_ids)
    agrupados: dict[uuid.UUID, list[ItemReglaAporte]] = {i: [] for i in ids}
    if not ids:
        return agrupados
    filas = db.execute(
        select(ItemReglaAporte).where(ItemReglaAporte.rule_id.in_(ids)).order_by(ItemReglaAporte.member_id)
    ).scalars()
    for item in filas:
        agrupados[item.rule_id].append(item)
    return agrupados


def listar_reglas(db: Session, hogar_id: uuid.UUID) -> list[ReglaAporte]:
    """Reglas del hogar: primero las generales, luego por categoría; más recientes primero."""
    return list(
        db.execute(
            select(ReglaAporte)
            .where(ReglaAporte.household_id == hogar_id)
            .order_by(ReglaAporte.categoria_id.is_(None).desc(), ReglaAporte.categoria_id, ReglaAporte.vigente_desde.desc())
        ).scalars()
    )


def crear_regla(db: Session, **campos) -> ReglaAporte:
    """Inserta la cabecera de una regla."""
    regla = ReglaAporte(**campos)
    db.add(regla)
    db.flush()
    return regla


def crear_items(
    db: Session,
    *,
    regla_id: uuid.UUID,
    hogar_id: uuid.UUID,
    items: Iterable[tuple[uuid.UUID, str, Decimal]],
) -> None:
    """Inserta los ítems (integrante, tipo, valor) de una regla."""
    for integrante_id, tipo, valor in items:
        db.add(
            ItemReglaAporte(
                rule_id=regla_id, household_id=hogar_id, member_id=integrante_id, tipo=tipo, valor=valor
            )
        )
    db.flush()


# ---------------------------------------------------------------------------
# Repartos (obligación esperada de cada integrante por cada gasto)
# ---------------------------------------------------------------------------
def crear_partes(
    db: Session,
    *,
    hogar_id: uuid.UUID,
    movimiento_id: uuid.UUID,
    regla_id: uuid.UUID,
    partes: Iterable[tuple[uuid.UUID, str, Decimal, Decimal]],
) -> None:
    """Inserta la 'foto' del reparto: (integrante, tipo, valor, importe) por cada integrante."""
    for integrante_id, tipo, valor, importe in partes:
        db.add(
            ParteAporte(
                household_id=hogar_id,
                transaction_id=movimiento_id,
                member_id=integrante_id,
                rule_id=regla_id,
                tipo=tipo,
                valor=valor,
                importe=importe,
            )
        )
    db.flush()


def partes_de_movimiento(
    db: Session, hogar_id: uuid.UUID, movimiento_id: uuid.UUID
) -> list[ParteAporte]:
    """Reparto aplicado a un movimiento."""
    return list(
        db.execute(
            select(ParteAporte)
            .where(ParteAporte.household_id == hogar_id, ParteAporte.transaction_id == movimiento_id)
            .order_by(ParteAporte.member_id)
        ).scalars()
    )


# ---------------------------------------------------------------------------
# Resúmenes por integrante (solo movimientos confirmados)
# ---------------------------------------------------------------------------
def _filtrar_periodo(consulta, desde: date | None, hasta: date | None):
    """Aplica el rango de fechas (opcional) sobre la fecha del movimiento."""
    if desde is not None:
        consulta = consulta.where(Movimiento.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(Movimiento.fecha <= hasta)
    return consulta


def esperado_por_integrante(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> dict[uuid.UUID, Decimal]:
    """Obligación esperada: suma de las partes de gastos confirmados."""
    consulta = (
        select(ParteAporte.member_id, func.sum(ParteAporte.importe))
        .join(Movimiento, Movimiento.id == ParteAporte.transaction_id)
        .where(Movimiento.household_id == hogar_id, Movimiento.estado == _CONFIRMADA)
        .group_by(ParteAporte.member_id)
    )
    return {fila[0]: fila[1] for fila in db.execute(_filtrar_periodo(consulta, desde, hasta)).all()}


def aportes_por_integrante(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> dict[uuid.UUID, Decimal]:
    """Dinero que cada integrante entregó al fondo común (movimientos 'aporte' confirmados)."""
    consulta = (
        select(Movimiento.pagador_id, func.sum(LineaMovimiento.importe))
        .join(LineaMovimiento, LineaMovimiento.transaction_id == Movimiento.id)
        .where(
            Movimiento.household_id == hogar_id,
            Movimiento.tipo == TipoMovimiento.APORTE.value,
            Movimiento.estado == _CONFIRMADA,
            LineaMovimiento.importe > 0,
        )
        .group_by(Movimiento.pagador_id)
    )
    return {fila[0]: fila[1] for fila in db.execute(_filtrar_periodo(consulta, desde, hasta)).all()}


def pagos_directos_por_integrante(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> dict[uuid.UUID, Decimal]:
    """Gastos del hogar pagados desde la cuenta personal de un integrante (con su propio dinero)."""
    consulta = (
        select(Cuenta.propietario_id, func.sum(-LineaMovimiento.importe))
        .join(LineaMovimiento, LineaMovimiento.account_id == Cuenta.id)
        .join(Movimiento, Movimiento.id == LineaMovimiento.transaction_id)
        .where(
            Movimiento.household_id == hogar_id,
            Movimiento.tipo.in_(TIPOS_GASTO_HOGAR),
            Movimiento.estado == _CONFIRMADA,
            Cuenta.tipo == "personal",
            LineaMovimiento.importe < 0,
        )
        .group_by(Cuenta.propietario_id)
    )
    return {fila[0]: fila[1] for fila in db.execute(_filtrar_periodo(consulta, desde, hasta)).all()}


def reembolsos_por_integrante(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> dict[uuid.UUID, Decimal]:
    """Dinero que el fondo común le devolvió a cada integrante (movimientos 'reembolso' confirmados)."""
    consulta = (
        select(Movimiento.beneficiario_id, func.sum(LineaMovimiento.importe))
        .join(LineaMovimiento, LineaMovimiento.transaction_id == Movimiento.id)
        .where(
            Movimiento.household_id == hogar_id,
            Movimiento.tipo == TipoMovimiento.REEMBOLSO.value,
            Movimiento.estado == _CONFIRMADA,
            LineaMovimiento.importe > 0,
        )
        .group_by(Movimiento.beneficiario_id)
    )
    return {fila[0]: fila[1] for fila in db.execute(_filtrar_periodo(consulta, desde, hasta)).all()}


def gastos_sin_distribuir(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> Decimal:
    """Total de gastos confirmados del período a los que no se les aplicó ninguna regla."""
    consulta = (
        select(func.coalesce(func.sum(-LineaMovimiento.importe), 0))
        .join(Movimiento, Movimiento.id == LineaMovimiento.transaction_id)
        .where(
            Movimiento.household_id == hogar_id,
            Movimiento.tipo.in_(TIPOS_GASTO_HOGAR),
            Movimiento.estado == _CONFIRMADA,
            LineaMovimiento.importe < 0,
            ~exists().where(ParteAporte.transaction_id == Movimiento.id),
        )
    )
    return db.execute(_filtrar_periodo(consulta, desde, hasta)).scalar_one()