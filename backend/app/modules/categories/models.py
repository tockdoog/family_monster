# backend/app/modules/categories/models.py
# Categorías de gasto del hogar (Agua, Mercado, Arriendo...). Son configurables por hogar.

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, UniqueConstraint, Uuid, text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin


class Categoria(IdUuidMixin, MarcaTiempoMixin, Base):
    """Categoría para clasificar gastos, ingresos y obligaciones."""

    __tablename__ = "categories"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    # Una categoría con historial no se borra: se desactiva y deja de ofrecerse.
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        # Permite que movimientos, obligaciones y reglas referencien (categoría, hogar).
        UniqueConstraint("id", "household_id", name="uq_categories_id_hogar"),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        # No se repiten nombres dentro del hogar (sin distinguir mayúsculas).
        Index("uq_categories_hogar_nombre", "household_id", text("lower(nombre)"), unique=True),
    )