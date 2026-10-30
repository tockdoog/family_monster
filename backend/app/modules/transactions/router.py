# backend/app/modules/transactions/router.py
# Endpoints de movimientos: /api/v1/transactions. Validan permisos y delegan en el servicio.

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.transactions import service
from app.modules.transactions.schemas import (
    MovimientoSalida,
    SolicitudMovimiento,
    SolicitudReversion,
)
from app.shared.idempotency import ClaveIdempotencia
from app.shared.pagination import Pagina, Paginacion

router = APIRouter(prefix="/transactions", tags=["Movimientos"])


@router.post(
    "",
    response_model=MovimientoSalida,
    status_code=201,
    summary="Registrar ingreso, gasto o transferencia",
)
def registrar(
    datos: SolicitudMovimiento,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REGISTRAR_MOVIMIENTOS))],
    db: SesionBD,
) -> MovimientoSalida:
    """Crea el movimiento (201). Si la clave ya se usó con los mismos datos, devuelve el original (200)."""
    movimiento, creado = service.registrar_movimiento(db, contexto, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return movimiento


@router.get("", response_model=Pagina[MovimientoSalida], summary="Listar movimientos")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    pagina: Paginacion,
    tipo: Literal[
        "ingreso", "gasto", "transferencia", "reversion", "aporte", "reembolso",
        "pago_obligacion", "desembolso_prestamo", "pago_cuota",
    ] | None = None,
    estado: Literal["confirmada", "revertida"] | None = None,
    cuenta_id: uuid.UUID | None = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> Pagina[MovimientoSalida]:
    """Movimientos del hogar, del más reciente al más antiguo, con filtros opcionales."""
    return service.listar_movimientos(
        db,
        contexto.hogar_id,
        pagina,
        tipo=tipo,
        estado=estado,
        cuenta_id=cuenta_id,
        desde=desde,
        hasta=hasta,
    )


@router.post(
    "/{movimiento_id}/reverse",
    response_model=MovimientoSalida,
    status_code=201,
    summary="Revertir un movimiento",
)
def revertir(
    movimiento_id: uuid.UUID,
    datos: SolicitudReversion,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REVERTIR_MOVIMIENTOS))],
    db: SesionBD,
) -> MovimientoSalida:
    """Contrarresta el movimiento con una reversión trazable (motivo obligatorio)."""
    reversion, creada = service.revertir_movimiento(db, contexto, movimiento_id, datos, clave)
    if not creada:
        respuesta.status_code = 200
    return reversion