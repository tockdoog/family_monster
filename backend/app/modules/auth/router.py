# backend/app/modules/auth/router.py
# Endpoints de autenticación: /api/v1/auth/login, /logout y /me. Sin lógica de negocio.

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import ContextoUsuario, obtener_contexto
from app.core.permissions import PERMISOS_POR_ROL, Rol
from app.core.security import eliminar_cookie_acceso, establecer_cookie_acceso
from app.db.session import SesionBD
from app.modules.auth import service
from app.modules.auth.schemas import HogarResumen, SesionSalida, SolicitudLogin, UsuarioSalida

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _permisos_de(rol: Rol) -> list[str]:
    """Lista ordenada de permisos del rol para mostrar en la interfaz."""
    return sorted(p.value for p in PERMISOS_POR_ROL[rol])


@router.post("/login", response_model=SesionSalida, summary="Iniciar sesión")
def iniciar_sesion(datos: SolicitudLogin, respuesta: Response, db: SesionBD) -> SesionSalida:
    """Verifica credenciales y entrega el token en una cookie HttpOnly."""
    sesion = service.iniciar_sesion(db, datos.email, datos.contrasena)
    establecer_cookie_acceso(respuesta, sesion.token)
    rol = Rol(sesion.membresia.rol)
    return SesionSalida(
        usuario=UsuarioSalida(
            id=sesion.usuario.id,
            email=sesion.usuario.email,
            nombre_completo=sesion.usuario.nombre_completo,
        ),
        hogar=HogarResumen(id=sesion.hogar.id, nombre=sesion.hogar.nombre),
        rol=rol.value,
        permisos=_permisos_de(rol),
    )


@router.post("/logout", status_code=204, summary="Cerrar sesión")
def cerrar_sesion(respuesta: Response) -> Response:
    """Elimina la cookie de sesión del navegador."""
    eliminar_cookie_acceso(respuesta)
    respuesta.status_code = 204
    return respuesta


@router.get("/me", response_model=SesionSalida, summary="Usuario autenticado")
def quien_soy(contexto: Annotated[ContextoUsuario, Depends(obtener_contexto)]) -> SesionSalida:
    """Devuelve la identidad, el hogar y el rol de la sesión actual."""
    return SesionSalida(
        usuario=UsuarioSalida(
            id=contexto.usuario_id, email=contexto.email, nombre_completo=contexto.nombre_completo
        ),
        hogar=HogarResumen(id=contexto.hogar_id, nombre=contexto.hogar_nombre),
        rol=contexto.rol.value,
        permisos=_permisos_de(contexto.rol),
    )