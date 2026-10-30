# backend/app/modules/categories/router.py
# Endpoints de categorías: /api/v1/categories.

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.categories import service
from app.modules.categories.schemas import (
    CategoriaSalida,
    SolicitudActualizarCategoria,
    SolicitudCrearCategoria,
)

router = APIRouter(prefix="/categories", tags=["Categorías"])


@router.get("", response_model=list[CategoriaSalida], summary="Listar categorías")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> list[CategoriaSalida]:
    """Categorías del hogar de la sesión."""
    return service.listar_categorias(db, contexto.hogar_id)


@router.post("", response_model=CategoriaSalida, status_code=201, summary="Crear categoría")
def crear(
    datos: SolicitudCrearCategoria,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_CATEGORIAS))],
    db: SesionBD,
) -> CategoriaSalida:
    """Crea una categoría (solo administradores)."""
    return service.crear_categoria(db, contexto, datos)


@router.patch("/{categoria_id}", response_model=CategoriaSalida, summary="Renombrar o desactivar")
def actualizar(
    categoria_id: uuid.UUID,
    datos: SolicitudActualizarCategoria,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_CATEGORIAS))],
    db: SesionBD,
) -> CategoriaSalida:
    """Renombra o activa/desactiva una categoría (solo administradores)."""
    return service.actualizar_categoria(db, contexto, categoria_id, datos)