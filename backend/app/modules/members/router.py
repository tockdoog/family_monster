# backend/app/modules/members/router.py
# Endpoints de integrantes: /api/v1/members. Cada uno valida el permiso antes de actuar.

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.members import service
from app.modules.members.schemas import (
    IntegranteSalida,
    SolicitudCrearIntegrante,
    SolicitudOtorgarAcceso,
)

router = APIRouter(prefix="/members", tags=["Integrantes"])


@router.get("", response_model=list[IntegranteSalida], summary="Listar integrantes")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> list[IntegranteSalida]:
    """Lista los integrantes del hogar de la sesión."""
    return service.listar_integrantes(db, contexto.hogar_id)


@router.post("", response_model=IntegranteSalida, status_code=201, summary="Crear integrante")
def crear(
    datos: SolicitudCrearIntegrante,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_INTEGRANTES))],
    db: SesionBD,
) -> IntegranteSalida:
    """Registra un integrante en el hogar (solo administradores)."""
    return service.crear_integrante(db, contexto.hogar_id, contexto.usuario_id, datos.nombre)


@router.post(
    "/{integrante_id}/acceso",
    response_model=IntegranteSalida,
    status_code=201,
    summary="Otorgar acceso a la aplicación",
)
def otorgar_acceso(
    integrante_id: uuid.UUID,
    datos: SolicitudOtorgarAcceso,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_INTEGRANTES))],
    db: SesionBD,
) -> IntegranteSalida:
    """Crea las credenciales de un integrante existente (solo administradores)."""
    return service.otorgar_acceso(
        db,
        contexto.hogar_id,
        contexto.usuario_id,
        integrante_id,
        email=datos.email,
        contrasena=datos.contrasena,
        rol=datos.rol,
    )