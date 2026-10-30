# backend/app/modules/audit/repository.py
# Acceso a datos de la bitácora. Solo inserta y consulta; nunca modifica ni borra.

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import RegistroAuditoria
from app.shared.pagination import ParametrosPagina


def insertar(
    db: Session,
    *,
    household_id: uuid.UUID,
    usuario_id: uuid.UUID,
    accion: str,
    entidad: str,
    entidad_id: uuid.UUID,
    motivo: str | None,
    detalle: dict[str, Any] | None,
) -> RegistroAuditoria:
    """Inserta un registro dentro de la transacción en curso."""
    registro = RegistroAuditoria(
        household_id=household_id,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        motivo=motivo,
        detalle=detalle,
    )
    db.add(registro)
    db.flush()
    return registro


def listar(
    db: Session, hogar_id: uuid.UUID, pagina: ParametrosPagina
) -> tuple[list[RegistroAuditoria], int]:
    """Registros del hogar, del más reciente al más antiguo, con el total."""
    base = select(RegistroAuditoria).where(RegistroAuditoria.household_id == hogar_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    filas = db.execute(
        base.order_by(RegistroAuditoria.creado_en.desc(), RegistroAuditoria.id)
        .limit(pagina.limite)
        .offset(pagina.desplazamiento)
    ).scalars()
    return list(filas), total