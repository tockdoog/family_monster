# backend/app/modules/households/router.py
# Endpoints del hogar: GET /api/v1/households/current y POST /api/v1/instalacion.

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.households import service
from app.modules.households.schemas import HogarSalida, SolicitudInstalacion

router = APIRouter(prefix="/households", tags=["Hogar"])
router_instalacion = APIRouter(prefix="/instalacion", tags=["Instalación"])


@router.get("/current", response_model=HogarSalida, summary="Hogar actual")
def hogar_actual(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> HogarSalida:
    """Devuelve el hogar de la sesión; el identificador nunca se recibe del cliente."""
    return HogarSalida.model_validate(service.obtener_hogar_actual(db, contexto.hogar_id))


@router_instalacion.post("", response_model=HogarSalida, status_code=201, summary="Instalación inicial")
def instalar(
    datos: SolicitudInstalacion,
    db: SesionBD,
    token: Annotated[str | None, Header(alias="X-Setup-Token")] = None,
) -> HogarSalida:
    """Crea el primer hogar y su administrador. Requiere SETUP_TOKEN y solo funciona una vez."""
    return HogarSalida.model_validate(service.instalar_hogar_inicial(db, datos, token))