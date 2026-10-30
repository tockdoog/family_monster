# backend/app/modules/members/models.py
# Integrantes financieros del hogar. Existen aparte de los usuarios: una persona puede
# aparecer en las cuentas aunque no tenga acceso a la aplicación.

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin


class Integrante(IdUuidMixin, MarcaTiempoMixin, Base):
    """Persona del hogar sobre la que se registran aportes, pagos y deudas."""

    __tablename__ = "members"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # Opcional: solo se llena cuando el integrante tiene acceso a la aplicación.
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        # Un usuario solo puede estar vinculado a un integrante.
        UniqueConstraint("user_id"),
        # Permite que cuentas y movimientos referencien (integrante, hogar) y garanticen el mismo hogar.
        UniqueConstraint("id", "household_id", name="uq_members_id_hogar"),
        # Integridad entre hogar y usuario: el usuario vinculado debe pertenecer a ESTE mismo hogar.
        ForeignKeyConstraint(
            ["user_id", "household_id"],
            ["memberships.user_id", "memberships.household_id"],
            ondelete="RESTRICT",
            name="fk_members_usuario_hogar_memberships",
        ),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        # No se repiten nombres dentro del hogar (sin distinguir mayúsculas).
        Index("uq_members_hogar_nombre", "household_id", text("lower(nombre)"), unique=True),
    )