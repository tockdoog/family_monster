# backend/app/core/dependencies.py
# Dependencias de FastAPI que identifican al usuario, su hogar y su rol a partir de la cookie
# de sesión. El hogar y el rol SIEMPRE salen de la base de datos, nunca de datos del cliente.

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.exceptions import NoAutenticado
from app.core.permissions import Permiso, Rol, exigir_permiso
from app.core.security import NOMBRE_COOKIE_ACCESO, decodificar_token_acceso
from app.db.session import SesionBD
from app.modules.auth import repository


@dataclass(frozen=True)
class ContextoUsuario:
    """Identidad verificada de quien hace la solicitud."""

    usuario_id: uuid.UUID
    email: str
    nombre_completo: str
    hogar_id: uuid.UUID
    hogar_nombre: str
    rol: Rol


def obtener_contexto(solicitud: Request, db: SesionBD) -> ContextoUsuario:
    """Valida la cookie y carga usuario, hogar y rol desde la base de datos."""
    token = solicitud.cookies.get(NOMBRE_COOKIE_ACCESO)
    if not token:
        raise NoAutenticado()

    datos = decodificar_token_acceso(token)
    try:
        usuario_id = uuid.UUID(datos.usuario_id)
    except ValueError as exc:
        raise NoAutenticado("La sesión no es válida o ya venció.") from exc

    fila = repository.contexto_por_usuario_id(db, usuario_id)
    # Un usuario desactivado o sin membresía activa pierde acceso de inmediato, aunque su token siga vigente.
    if fila is None or not fila[0].activo:
        raise NoAutenticado("La sesión no es válida o ya venció.")

    usuario, membresia, hogar = fila
    return ContextoUsuario(
        usuario_id=usuario.id,
        email=usuario.email,
        nombre_completo=usuario.nombre_completo,
        hogar_id=hogar.id,
        hogar_nombre=hogar.nombre,
        rol=Rol(membresia.rol),
    )


def requiere_permiso(permiso: Permiso) -> Callable[[ContextoUsuario], ContextoUsuario]:
    """Crea una dependencia que exige un permiso concreto y devuelve el contexto validado."""

    def _dependencia(
        contexto: Annotated[ContextoUsuario, Depends(obtener_contexto)],
    ) -> ContextoUsuario:
        exigir_permiso(contexto.rol, permiso)
        return contexto

    return _dependencia