# backend/app/modules/households/models.py
# Tablas del hogar y de la pertenencia de cada usuario a un hogar con su rol.

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin


class Hogar(IdUuidMixin, MarcaTiempoMixin, Base):
    """Unidad privada cuyos datos financieros están aislados de los demás hogares."""

    __tablename__ = "households"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # Versión 1: solo pesos colombianos. La columna permite crecer a otras monedas.
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, server_default="COP")
    zona_horaria: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="America/Bogota"
    )

    __table_args__ = (
        CheckConstraint("moneda = 'COP'", name="moneda_soportada"),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
    )


class Membresia(IdUuidMixin, MarcaTiempoMixin, Base):
    """Une a un usuario con su hogar y define su rol (admin o miembro)."""

    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        # Versión 1: un usuario pertenece a un solo hogar (quitar esta restricción permitirá varios).
        UniqueConstraint("user_id", name="uq_memberships_un_hogar_por_usuario"),
        # Necesaria para que 'members' pueda referenciar el par (usuario, hogar) y garantizar coherencia.
        UniqueConstraint("user_id", "household_id", name="uq_memberships_usuario_hogar"),
        CheckConstraint("rol IN ('admin', 'miembro')", name="rol_valido"),
    )