# backend/app/modules/audit/schemas.py
# Contrato de salida de la bitácora de auditoría.

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditoriaSalida(BaseModel):
    """Un registro de la bitácora."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID
    accion: str
    entidad: str
    entidad_id: uuid.UUID
    motivo: str | None
    detalle: dict[str, Any] | None
    creado_en: datetime