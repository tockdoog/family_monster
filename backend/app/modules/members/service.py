# backend/app/modules/members/service.py
# Reglas de negocio de integrantes: listado, alta y otorgamiento de acceso a la aplicación.

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import Conflicto, NoEncontrado
from app.core.security import hashear_contrasena, validar_politica_contrasena
from app.modules.audit import service as auditoria
from app.modules.auth import repository as repo_auth
from app.modules.households import repository as repo_hogares
from app.modules.members import repository
from app.modules.members.models import Integrante
from app.modules.members.schemas import IntegranteSalida


def _a_salida(integrante: Integrante, rol: str | None) -> IntegranteSalida:
    """Convierte el modelo en el contrato de salida."""
    return IntegranteSalida(
        id=integrante.id,
        nombre=integrante.nombre,
        activo=integrante.activo,
        tiene_acceso=integrante.user_id is not None,
        rol=rol,
    )


def listar_integrantes(db: Session, hogar_id: uuid.UUID) -> list[IntegranteSalida]:
    """Integrantes del hogar de la sesión."""
    return [_a_salida(i, rol) for i, rol in repository.listar_con_rol(db, hogar_id)]


def crear_integrante(
    db: Session, hogar_id: uuid.UUID, actor_id: uuid.UUID, nombre: str
) -> IntegranteSalida:
    """Registra un integrante sin acceso a la aplicación y deja constancia en la auditoría."""
    try:
        integrante = repository.crear_integrante(db, household_id=hogar_id, nombre=nombre)
    except IntegrityError as exc:
        # La restricción de nombre único por hogar es la garantía final, incluso ante solicitudes simultáneas.
        raise Conflicto("Ya existe un integrante con ese nombre en el hogar.") from exc
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=actor_id,
        accion="integrante_creado",
        entidad="member",
        entidad_id=integrante.id,
        detalle={"nombre": integrante.nombre},
    )
    return _a_salida(integrante, None)


def otorgar_acceso(
    db: Session,
    hogar_id: uuid.UUID,
    actor_id: uuid.UUID,
    integrante_id: uuid.UUID,
    *,
    email: str,
    contrasena: str,
    rol: str,
) -> IntegranteSalida:
    """Crea usuario y membresía para un integrante existente, todo en una sola transacción."""
    # La búsqueda filtra por hogar: un integrante de otro hogar se responde como 'no existe'.
    integrante = repository.obtener_por_id(db, hogar_id, integrante_id)
    if integrante is None:
        raise NoEncontrado("El integrante no existe.")
    if integrante.user_id is not None:
        raise Conflicto("Este integrante ya tiene acceso a la aplicación.")

    validar_politica_contrasena(contrasena)
    if repo_auth.usuario_por_email(db, email) is not None:
        raise Conflicto("Ese correo ya está en uso.")

    try:
        usuario = repo_auth.crear_usuario(
            db,
            email=email,
            password_hash=hashear_contrasena(contrasena),
            nombre_completo=integrante.nombre,
        )
        repo_hogares.crear_membresia(db, user_id=usuario.id, household_id=hogar_id, rol=rol)
        integrante.user_id = usuario.id
        db.flush()
    except IntegrityError as exc:
        raise Conflicto("Ese correo ya está en uso.") from exc
    # Se registra el rol otorgado, nunca la contraseña ni el hash.
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=actor_id,
        accion="acceso_otorgado",
        entidad="member",
        entidad_id=integrante.id,
        detalle={"rol": rol, "usuario_id": str(usuario.id)},
    )
    return _a_salida(integrante, rol)