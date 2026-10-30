# backend/app/modules/contributions/router.py
# Endpoints de aportes: /api/v1/contribution-rules y /api/v1/contributions.

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.contributions import service
from app.modules.contributions.schemas import (
    ParteSalida,
    ReglaSalida,
    ResumenAportes,
    SolicitudAporte,
    SolicitudReembolso,
    SolicitudRegla,
)
from app.modules.transactions.schemas import MovimientoSalida
from app.shared.idempotency import ClaveIdempotencia

router_reglas = APIRouter(prefix="/contribution-rules", tags=["Aportes"])
router = APIRouter(prefix="/contributions", tags=["Aportes"])


@router_reglas.post("", response_model=ReglaSalida, status_code=201, summary="Crear regla de reparto")
def crear_regla(
    datos: SolicitudRegla,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.GESTIONAR_REGLAS_APORTES))],
    db: SesionBD,
) -> ReglaSalida:
    """Crea una regla con vigencia; reemplaza a la anterior del mismo alcance desde su fecha de inicio."""
    return service.crear_regla(db, contexto, datos)


@router_reglas.get("", response_model=list[ReglaSalida], summary="Listar reglas de reparto")
def listar_reglas(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> list[ReglaSalida]:
    """Reglas vigentes e históricas del hogar."""
    return service.listar_reglas(db, contexto.hogar_id)


@router.get("/summary", response_model=ResumenAportes, summary="Aportes esperados y reales")
def resumen(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    desde: date | None = None,
    hasta: date | None = None,
) -> ResumenAportes:
    """Lo que cada integrante debía aportar, lo que puso y su saldo (mes actual por defecto)."""
    return service.resumen_aportes(db, contexto.hogar_id, desde, hasta)


@router.get(
    "/distributions/{movimiento_id}", response_model=list[ParteSalida], summary="Reparto de un gasto"
)
def reparto(
    movimiento_id: uuid.UUID,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
) -> list[ParteSalida]:
    """Foto del reparto aplicado a un gasto (regla y valores usados en ese momento)."""
    return service.reparto_de_movimiento(db, contexto.hogar_id, movimiento_id)


@router.post("", response_model=MovimientoSalida, status_code=201, summary="Registrar un aporte")
def aporte(
    datos: SolicitudAporte,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REGISTRAR_MOVIMIENTOS))],
    db: SesionBD,
) -> MovimientoSalida:
    """Dinero que un integrante entrega al fondo común (201; 200 si es una repetición idempotente)."""
    movimiento, creado = service.registrar_aporte(db, contexto, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return movimiento


@router.post(
    "/reimbursements", response_model=MovimientoSalida, status_code=201, summary="Registrar un reembolso"
)
def reembolso(
    datos: SolicitudReembolso,
    clave: ClaveIdempotencia,
    respuesta: Response,
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.REGISTRAR_MOVIMIENTOS))],
    db: SesionBD,
) -> MovimientoSalida:
    """Devuelve dinero a quien pagó gastos del hogar con su cuenta personal (201; 200 si se repite)."""
    movimiento, creado = service.registrar_reembolso(db, contexto, datos, clave)
    if not creado:
        respuesta.status_code = 200
    return movimiento