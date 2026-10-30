# backend/app/modules/obligations/models.py
# Obligaciones (facturas, servicios, deudas) y sus pagos. El saldo pendiente y el estado se
# derivan de los pagos confirmados: no se guardan, así nunca se contradicen con el libro.

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin, TipoDinero


class Obligacion(IdUuidMixin, MarcaTiempoMixin, Base):
    """Cuenta por pagar del hogar."""

    __tablename__ = "obligations"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False)
    categoria_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    importe_original: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    fecha_creacion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    # Acreedor o proveedor al que se le debe.
    acreedor: Mapped[str] = mapped_column(String(120), nullable=False)
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Anulación trazable: nunca se borra; queda quién, cuándo y por qué.
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    anulada_por: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_obligations_id_hogar"),
        ForeignKeyConstraint(
            ["categoria_id", "household_id"],
            ["categories.id", "categories.household_id"],
            ondelete="RESTRICT",
            name="fk_obligations_categoria_hogar_categories",
        ),
        ForeignKeyConstraint(
            ["responsable_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_obligations_responsable_hogar_members",
        ),
        CheckConstraint("importe_original > 0", name="importe_positivo"),
        CheckConstraint("fecha_vencimiento >= fecha_creacion", name="vencimiento_coherente"),
        CheckConstraint("length(trim(descripcion)) > 0", name="descripcion_no_vacia"),
        CheckConstraint("length(trim(acreedor)) > 0", name="acreedor_no_vacio"),
        # Anulada <=> tiene fecha, motivo y responsable.
        CheckConstraint(
            "(anulada_en IS NULL) = (motivo_anulacion IS NULL) AND (anulada_en IS NULL) = (anulada_por IS NULL)",
            name="anulacion_coherente",
        ),
    )


class PagoObligacion(IdUuidMixin, Base):
    """Vínculo entre una obligación y el movimiento real que la pagó (total o parcialmente)."""

    __tablename__ = "obligation_payments"

    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    obligation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    # Un movimiento paga como máximo una obligación.
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["obligation_id", "household_id"],
            ["obligations.id", "obligations.household_id"],
            ondelete="RESTRICT",
            name="fk_obligation_payments_obligacion_hogar_obligations",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_obligation_payments_movimiento_hogar_transactions",
        ),
        UniqueConstraint("transaction_id", name="uq_obligation_payments_movimiento"),
        CheckConstraint("importe > 0", name="importe_positivo"),
    )