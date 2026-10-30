# backend/app/modules/auth/repository.py
# Consultas a la base de datos del módulo de autenticación.

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.modules.auth.models import IntentoLogin, Usuario
from app.modules.households.models import Hogar, Membresia


def usuario_por_email(db: Session, email: str) -> Usuario | None:
    """Busca un usuario por su correo (ya normalizado a minúsculas)."""
    return db.execute(select(Usuario).where(Usuario.email == email)).scalar_one_or_none()


def existe_algun_usuario(db: Session) -> bool:
    """Indica si ya hay al menos un usuario registrado."""
    return db.execute(select(Usuario.id).limit(1)).first() is not None


def contexto_por_usuario_id(
    db: Session, usuario_id: uuid.UUID
) -> tuple[Usuario, Membresia, Hogar] | None:
    """Carga usuario, membresía activa y hogar en una sola consulta."""
    fila = db.execute(
        select(Usuario, Membresia, Hogar)
        .join(Membresia, Membresia.user_id == Usuario.id)
        .join(Hogar, Hogar.id == Membresia.household_id)
        .where(Usuario.id == usuario_id, Membresia.activo.is_(True))
    ).first()
    return None if fila is None else (fila[0], fila[1], fila[2])


def crear_usuario(db: Session, *, email: str, password_hash: str, nombre_completo: str) -> Usuario:
    """Inserta un usuario nuevo y devuelve el objeto con su identificador."""
    usuario = Usuario(email=email, password_hash=password_hash, nombre_completo=nombre_completo)
    db.add(usuario)
    db.flush()
    return usuario


def obtener_intento_bloqueando(db: Session, clave: str, ahora: datetime) -> IntentoLogin:
    """Obtiene (creando si no existe) el contador de intentos con bloqueo de fila.

    El INSERT ... ON CONFLICT DO NOTHING evita errores si dos solicitudes llegan a la vez,
    y FOR UPDATE serializa las actualizaciones del mismo correo.
    """
    db.execute(
        pg_insert(IntentoLogin)
        .values(clave=clave, intentos=0, primer_intento_en=ahora)
        .on_conflict_do_nothing(index_elements=["clave"])
    )
    return db.execute(
        select(IntentoLogin).where(IntentoLogin.clave == clave).with_for_update()
    ).scalar_one()


def eliminar_intento(db: Session, clave: str) -> None:
    """Borra el contador tras un inicio de sesión correcto."""
    db.execute(delete(IntentoLogin).where(IntentoLogin.clave == clave))