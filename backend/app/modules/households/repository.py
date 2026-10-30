# backend/app/modules/households/repository.py
# Consultas a la base de datos de hogares y membresías.

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.households.models import Hogar, Membresia

# Identificador del candado que impide dos instalaciones iniciales simultáneas.
_CANDADO_INSTALACION = 7101


def bloquear_instalacion(db: Session) -> None:
    """Candado de transacción: serializa las instalaciones iniciales concurrentes."""
    db.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": _CANDADO_INSTALACION})


def crear_hogar(db: Session, *, nombre: str) -> Hogar:
    """Inserta un hogar nuevo (moneda y zona horaria usan los valores por defecto)."""
    hogar = Hogar(nombre=nombre)
    db.add(hogar)
    db.flush()
    return hogar


def crear_membresia(db: Session, *, user_id: uuid.UUID, household_id: uuid.UUID, rol: str) -> Membresia:
    """Inserta la pertenencia de un usuario a un hogar con su rol."""
    membresia = Membresia(user_id=user_id, household_id=household_id, rol=rol)
    db.add(membresia)
    db.flush()
    return membresia


def obtener_hogar(db: Session, hogar_id: uuid.UUID) -> Hogar | None:
    """Busca un hogar por su identificador."""
    return db.get(Hogar, hogar_id)