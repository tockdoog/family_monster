# backend/app/modules/obligations/router.py
# Endpoints de obligaciones: /api/v1/obligations. Validan permisos y delegan en el servicio.

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.obligations import service
from app.modules.obligations.schemas import (
    EstadoObligacion,
    ObligacionDetalle,
    ObligacionSalida,
    PagoRegistradoSalida,
    SolicitudAnularObligacion,
    SolicitudCrearObligacion,
    SolicitudPagoObligacion,
)
from app.shared.idempotency import ClaveIdempotencia
from app.shared.pagination import Pagina, Paginacion

router = APIRouter(prefix="/obligations", tags=["Obligaciones"])


@router.post("", response_model=ObligacionSalida, status_code=201, summary="Registrar obligación")
def crear(
    datos: SolicitudCrearObligacion,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_OBLIGACIONES))],
    db: SesionBD,
) -> ObligacionSalida:
    """Registra una factura, servicio o deuda (solo administradores)."""
    return service.crear_obligacion(db, contexto, datos)


@router.get("", response_model=Pagina[ObligacionSalida], summary="Listar obligaciones")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    pagina: Paginacion,
    estado: EstadoObligacion | None = None,
) -> Pagina[ObligacionSalida]:
    """Obligaciones del hogar por fecha de vencimiento, con filtro opcional por estado."""
    return service.listar_obligaciones(db, contexto.hogar_id, pagina, estado)


@router.get("/{obligacion_id}", response_model=ObligacionDetalle, summary="Detalle con pagos")
def detalle(
    obligacion_id: uuid.UUID,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> ObligacionDetalle:
    """Una obligación con su saldo, estado y historial de pagos."""
    return service.obtener_obligacion(db, contexto.hogar_id, obligacion_id)


@router.post(
    "/{obligacion_id}/payments",
    response_model=PagoRegistradoSalida,
    status_code=201,
    summary="Pagar una obligación (total o parcial)",
)
def pagar(
    obligacion_id: uuid.UUID,
    datos: SolicitudPagoObligacion,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REGISTRAR_PAGOS))],
    db: SesionBD,
) -> PagoRegistradoSalida:
    """Crea el pago (201). Si la clave ya se usó con los mismos datos, devuelve el original (200)."""
    resultado, creado = service.pagar_obligacion(db, contexto, obligacion_id, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return resultado


@router.post("/{obligacion_id}/cancel", response_model=ObligacionSalida, summary="Anular una obligación")
def anular(
    obligacion_id: uuid.UUID,
    datos: SolicitudAnularObligacion,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_OBLIGACIONES))],
    db: SesionBD,
) -> ObligacionSalida:
    """Anula una obligación sin pagos (motivo obligatorio)."""
    return service.anular_obligacion(db, contexto, obligacion_id, datos)