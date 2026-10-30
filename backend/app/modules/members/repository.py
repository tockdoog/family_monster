# backend/app/modules/members/repository.py
# Consultas a la base de datos de integrantes. TODAS filtran por hogar.

import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.modules.households.models import Membresia
from app.modules.members.models import Integrante


def listar_con_rol(db: Session, hogar_id: uuid.UUID) -> list[tuple[Integrante, str | None]]:
    """Lista los integrantes del hogar junto con su rol de acceso (si lo tienen)."""
    filas = db.execute(
        select(Integrante, Membresia.rol)
        .outerjoin(
            Membresia,
            and_(
                Membresia.user_id == Integrante.user_id,
                Membresia.household_id == Integrante.household_id,
                Membresia.activo.is_(True),
            ),
        )
        .where(Integrante.household_id == hogar_id)
        .order_by(Integrante.nombre)
    ).all()
    return [(fila[0], fila[1]) for fila in filas]


def obtener_por_id(db: Session, hogar_id: uuid.UUID, integrante_id: uuid.UUID) -> Integrante | None:
    """Busca un integrante SOLO dentro del hogar indicado; los de otros hogares no existen."""
    return db.execute(
        select(Integrante).where(
            Integrante.id == integrante_id, Integrante.household_id == hogar_id
        )
    ).scalar_one_or_none()


def crear_integrante(
    db: Session, *, household_id: uuid.UUID, nombre: str, user_id: uuid.UUID | None = None
) -> Integrante:
    """Inserta un integrante nuevo."""
    integrante = Integrante(household_id=household_id, nombre=nombre, user_id=user_id)
    db.add(integrante)
    db.flush()
    return integrante


def bloquear(db: Session, hogar_id: uuid.UUID, integrante_id: uuid.UUID) -> Integrante | None:
    """Busca un integrante del hogar y lo bloquea (FOR UPDATE) para serializar operaciones sobre su saldo."""
    return db.execute(
        select(Integrante)
        .where(Integrante.id == integrante_id, Integrante.household_id == hogar_id)
        .with_for_update()
    ).scalar_one_or_none()