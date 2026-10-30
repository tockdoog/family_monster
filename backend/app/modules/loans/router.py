# backend/app/modules/loans/router.py
# Endpoints de préstamos: /api/v1/loans. Validan permisos y delegan en el servicio.

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.loans import service
from app.modules.loans.schemas import (
    EstadoPrestamo,
    PagoCuotaRegistradoSalida,
    PrestamoDetalle,
    PrestamoSalida,
    SolicitudPagoCuota,
    SolicitudPrestamo,
)
from app.shared.idempotency import ClaveIdempotencia
from app.shared.pagination import Pagina, Paginacion

router = APIRouter(prefix="/loans", tags=["Préstamos"])


@router.post("", response_model=PrestamoSalida, status_code=201, summary="Crear préstamo")
def crear(
    datos: SolicitudPrestamo,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_PRESTAMOS))],
    db: SesionBD,
) -> PrestamoSalida:
    """Crea el préstamo, sus cuotas y su desembolso (201; 200 si es una repetición idempotente)."""
    prestamo, creado = service.crear_prestamo(db, contexto, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return prestamo


@router.get("", response_model=Pagina[PrestamoSalida], summary="Listar préstamos")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    pagina: Paginacion,
    estado: EstadoPrestamo | None = None,
) -> Pagina[PrestamoSalida]:
    """Préstamos del hogar con su saldo, cuotas y estado."""
    return service.listar_prestamos(db, contexto.hogar_id, pagina, estado)


@router.get("/{prestamo_id}", response_model=PrestamoDetalle, summary="Detalle con pagos")
def detalle(
    prestamo_id: uuid.UUID,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> PrestamoDetalle:
    """Un préstamo con sus cuotas y el historial de pagos."""
    return service.obtener_prestamo(db, contexto.hogar_id, prestamo_id)


@router.post(
    "/{prestamo_id}/payments",
    response_model=PagoCuotaRegistradoSalida,
    status_code=201,
    summary="Pagar una cuota (total o parcial)",
)
def pagar(
    prestamo_id: uuid.UUID,
    datos: SolicitudPagoCuota,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REGISTRAR_PAGOS))],
    db: SesionBD,
) -> PagoCuotaRegistradoSalida:
    """Crea el pago (201). Si la clave ya se usó con los mismos datos, devuelve el original (200)."""
    resultado, creado = service.pagar_cuota(db, contexto, prestamo_id, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return resultado