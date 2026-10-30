# backend/app/modules/audit/service.py
# Registro de auditoría. Se invoca DENTRO de la misma transacción de la operación auditada:
# si la operación se revierte, su registro también; si se confirma, ambos quedan guardados.

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit import repository
from app.modules.audit.schemas import AuditoriaSalida
from app.shared.pagination import Pagina, ParametrosPagina


def registrar(
    db: Session,
    *,
    hogar_id: uuid.UUID,
    usuario_id: uuid.UUID,
    accion: str,
    entidad: str,
    entidad_id: uuid.UUID,
    motivo: str | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Guarda quién hizo qué, sobre qué y cuándo. El detalle no debe contener datos sensibles."""
    repository.insertar(
        db,
        household_id=hogar_id,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        motivo=motivo,
        detalle=detalle,
    )


def listar_auditoria(
    db: Session, hogar_id: uuid.UUID, pagina: ParametrosPagina
) -> Pagina[AuditoriaSalida]:
    """Bitácora paginada del hogar de la sesión."""
    registros, total = repository.listar(db, hogar_id, pagina)
    return Pagina[AuditoriaSalida](
        items=[AuditoriaSalida.model_validate(r) for r in registros],
        total=total,
        limite=pagina.limite,
        desplazamiento=pagina.desplazamiento,
    )