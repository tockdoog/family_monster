# backend/app/modules/households/service.py
# Reglas de negocio del hogar: instalación inicial y consulta del hogar actual.

import hmac
import uuid

from sqlalchemy.orm import Session

from app.core.config import obtener_configuracion
from app.core.exceptions import Conflicto, NoEncontrado, Prohibido
from app.core.permissions import Rol
from app.core.security import hashear_contrasena, validar_politica_contrasena
from app.modules.audit import service as auditoria
from app.modules.auth import repository as repo_auth
from app.modules.categories import service as servicio_categorias
from app.modules.households import repository
from app.modules.households.models import Hogar
from app.modules.households.schemas import SolicitudInstalacion
from app.modules.members import repository as repo_integrantes


def crear_hogar_con_admin(
    db: Session, *, nombre_hogar: str, nombre_completo: str, email: str, contrasena: str
) -> Hogar:
    """Crea hogar, usuario administrador, membresía e integrante en una sola transacción."""
    validar_politica_contrasena(contrasena)
    hogar = repository.crear_hogar(db, nombre=nombre_hogar)
    # Todo hogar nuevo recibe las categorías iniciales (Agua, Mercado, Arriendo...).
    servicio_categorias.sembrar_categorias_iniciales(db, hogar.id)
    usuario = repo_auth.crear_usuario(
        db,
        email=email,
        password_hash=hashear_contrasena(contrasena),
        nombre_completo=nombre_completo,
    )
    repository.crear_membresia(
        db, user_id=usuario.id, household_id=hogar.id, rol=Rol.ADMIN.value
    )
    repo_integrantes.crear_integrante(
        db, household_id=hogar.id, nombre=nombre_completo, user_id=usuario.id
    )
    # El primer administrador es quien crea el hogar: queda constancia del origen de todo.
    auditoria.registrar(
        db,
        hogar_id=hogar.id,
        usuario_id=usuario.id,
        accion="hogar_creado",
        entidad="household",
        entidad_id=hogar.id,
        detalle={"nombre": hogar.nombre},
    )
    return hogar


def instalar_hogar_inicial(
    db: Session, datos: SolicitudInstalacion, token_recibido: str | None
) -> Hogar:
    """Crea el primer hogar solo si hay token válido y no existe ningún usuario todavía."""
    token_esperado = obtener_configuracion().setup_token
    # Sin SETUP_TOKEN configurado el endpoint se comporta como si no existiera.
    if token_esperado is None:
        raise NoEncontrado()
    # Comparación en tiempo constante para no filtrar el token por diferencias de tiempo.
    if token_recibido is None or not hmac.compare_digest(
        token_recibido.encode("utf-8"), token_esperado.encode("utf-8")
    ):
        raise Prohibido("Token de instalación no válido.")

    # El candado evita que dos solicitudes simultáneas creen dos instalaciones.
    repository.bloquear_instalacion(db)
    if repo_auth.existe_algun_usuario(db):
        raise Conflicto("La instalación inicial ya fue realizada.")

    return crear_hogar_con_admin(
        db,
        nombre_hogar=datos.nombre_hogar,
        nombre_completo=datos.nombre_completo,
        email=datos.email,
        contrasena=datos.contrasena,
    )


def obtener_hogar_actual(db: Session, hogar_id: uuid.UUID) -> Hogar:
    """Devuelve el hogar del usuario autenticado (el identificador viene de la sesión)."""
    hogar = repository.obtener_hogar(db, hogar_id)
    if hogar is None:
        raise NoEncontrado("El hogar no existe.")
    return hogar