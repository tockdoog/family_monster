# backend/app/modules/audit/router.py
# Endpoint de consulta de la bitácora: GET /api/v1/audit (solo administradores).

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import ContextoUsuario, requiere_permiso
from app.core.permissions import Permiso
from app.db.session import SesionBD
from app.modules.audit import service
from app.modules.audit.schemas import AuditoriaSalida
from app.shared.pagination import Pagina, Paginacion

router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("", response_model=Pagina[AuditoriaSalida], summary="Consultar la bitácora")
def listar(
    contexto: Annotated[ContextoUsuario, Depends(requiere_permiso(Permiso.VER_AUDITORIA))],
    db: SesionBD,
    pagina: Paginacion,
) -> Pagina[AuditoriaSalida]:
    """Acciones sensibles del hogar, de la más reciente a la más antigua."""
    return service.listar_auditoria(db, contexto.hogar_id, pagina)