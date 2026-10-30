# backend/app/modules/reports/router.py
# Endpoints del panel principal y de informes: /api/v1/dashboard y /api/v1/reports.

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso, exigir_permiso
from app.db.session import SesionBD
from app.modules.reports import service
from app.modules.reports.schemas import InformeMensual, TableroSalida

router_tablero = APIRouter(prefix="/dashboard", tags=["Panel principal"])
router = APIRouter(prefix="/reports", tags=["Informes"])

# Mes en formato AAAA-MM (de 2000-01 a 2099-12).
_PATRON_MES = r"^20\d{2}-(0[1-9]|1[0-2])$"


@router_tablero.get("/summary", response_model=TableroSalida, summary="Panel principal")
def resumen(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    desde: date | None = None,
    hasta: date | None = None,
    dias_vencimientos: Annotated[int, Query(ge=1, le=365)] = 30,
) -> TableroSalida:
    """Saldos, ingresos, gastos, aportes, obligaciones, préstamos y próximos vencimientos (mes actual por defecto)."""
    return service.tablero(db, contexto.hogar_id, desde, hasta, dias_vencimientos)


@router.get("/monthly", response_model=InformeMensual, summary="Informe mensual (JSON o CSV)")
def mensual(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_FINANZAS))],
    db: SesionBD,
    mes: Annotated[str, Query(pattern=_PATRON_MES, description="Mes en formato AAAA-MM")],
    formato: Literal["json", "csv"] = "json",
):
    """Informe del mes. Con formato=csv descarga el archivo (requiere permiso de exportación)."""
    if formato == "csv":
        exigir_permiso(contexto.rol, Permiso.EXPORTAR_INFORMES)
        contenido = service.informe_mensual_csv(db, contexto, mes)
        return Response(
            content=contenido,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="informe-{mes}.csv"'},
        )
    return service.informe_mensual(db, contexto.hogar_id, mes)