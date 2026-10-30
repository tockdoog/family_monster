# backend/app/modules/categories/repository.py
# Consultas a la base de datos de categorías. Todas filtran por hogar.

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.categories.models import Categoria


def listar(db: Session, hogar_id: uuid.UUID) -> list[Categoria]:
    """Categorías del hogar ordenadas por nombre."""
    return list(
        db.execute(
            select(Categoria).where(Categoria.household_id == hogar_id).order_by(Categoria.nombre)
        ).scalars()
    )


def obtener(db: Session, hogar_id: uuid.UUID, categoria_id: uuid.UUID) -> Categoria | None:
    """Busca una categoría SOLO dentro del hogar indicado."""
    return db.execute(
        select(Categoria).where(Categoria.id == categoria_id, Categoria.household_id == hogar_id)
    ).scalar_one_or_none()


def nombres_por_id(db: Session, hogar_id: uuid.UUID) -> dict[uuid.UUID, str]:
    """Diccionario id -> nombre de las categorías del hogar (para informes)."""
    filas = db.execute(
        select(Categoria.id, Categoria.nombre).where(Categoria.household_id == hogar_id)
    ).all()
    return {fila[0]: fila[1] for fila in filas}


def crear(db: Session, *, household_id: uuid.UUID, nombre: str) -> Categoria:
    """Inserta una categoría nueva."""
    categoria = Categoria(household_id=household_id, nombre=nombre)
    db.add(categoria)
    db.flush()
    return categoria


def crear_varias(db: Session, *, household_id: uuid.UUID, nombres: Iterable[str]) -> None:
    """Inserta varias categorías de una vez (siembra inicial)."""
    db.add_all(Categoria(household_id=household_id, nombre=n) for n in nombres)
    db.flush()