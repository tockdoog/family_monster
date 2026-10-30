# backend/app/modules/accounts/router.py
# Endpoints de cuentas: /api/v1/accounts. Cada uno valida el permiso antes de actuar.

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.accounts import service
from app.modules.accounts.schemas import CuentaSalida, SolicitudCrearCuenta

router = APIRouter(prefix="/accounts", tags=["Cuentas"])


@router.get("", response_model=list[CuentaSalida], summary="Listar cuentas con su saldo")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> list[CuentaSalida]:
    """Cuentas del hogar con el saldo calculado desde los movimientos confirmados."""
    return service.listar_cuentas(db, contexto.hogar_id)


@router.post("", response_model=CuentaSalida, status_code=201, summary="Crear cuenta")
def crear(
    datos: SolicitudCrearCuenta,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_CUENTAS))],
    db: SesionBD,
) -> CuentaSalida:
    """Crea una cuenta o fondo del hogar (solo administradores)."""
    return service.crear_cuenta(db, contexto, datos)