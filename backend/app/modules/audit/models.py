# backend/app/modules/audit/models.py
# Bitácora de auditoría: registro permanente de las acciones sensibles. Solo se inserta;
# un trigger de la base de datos impide modificar o borrar sus filas.

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin


class RegistroAuditoria(IdUuidMixin, Base):
    """Una acción realizada por un usuario sobre una entidad del hogar."""

    __tablename__ = "audit_logs"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Ejemplos de acción: movimiento_registrado, movimiento_revertido, cuenta_creada.
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # Motivo obligatorio en correcciones y anulaciones.
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Datos de contexto (ids, importes). NUNCA contraseñas, tokens ni datos sensibles.
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_audit_logs_hogar_fecha", "household_id", "creado_en"),)