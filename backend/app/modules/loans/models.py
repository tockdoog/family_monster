# backend/app/modules/loans/models.py
# Préstamos, cuotas y pagos de cuotas. El desembolso y cada pago son movimientos reales del
# libro; el saldo pendiente se deriva de los pagos confirmados.

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin, TipoDinero


class Prestamo(IdUuidMixin, MarcaTiempoMixin, Base):
    """Préstamo entre integrantes, al hogar (el hogar recibe) o del hogar (el hogar presta)."""

    __tablename__ = "loans"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Quien presta y quien recibe: un integrante, el hogar (ambos nulos) o un tercero (por nombre).
    prestamista_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    prestatario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    contraparte_nombre: Mapped[str | None] = mapped_column(String(120), nullable=True)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    # Total que se devolverá (incluye intereses si los hay): suma de las cuotas.
    total_a_pagar: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    numero_cuotas: Mapped[int] = mapped_column(Integer, nullable=False)
    condiciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Movimiento del libro que entregó el dinero.
    desembolso_transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    creado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_loans_id_hogar"),
        UniqueConstraint("desembolso_transaction_id", name="uq_loans_desembolso"),
        ForeignKeyConstraint(
            ["prestamista_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_loans_prestamista_hogar_members",
        ),
        ForeignKeyConstraint(
            ["prestatario_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_loans_prestatario_hogar_members",
        ),
        ForeignKeyConstraint(
            ["desembolso_transaction_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_loans_desembolso_hogar_transactions",
        ),
        CheckConstraint(
            "tipo IN ('entre_integrantes', 'al_hogar', 'del_hogar')", name="tipo_valido"
        ),
        # Las partes deben ser coherentes con el tipo de préstamo.
        CheckConstraint(
            "(tipo = 'entre_integrantes' AND prestamista_id IS NOT NULL AND prestatario_id IS NOT NULL "
            "AND contraparte_nombre IS NULL AND prestamista_id <> prestatario_id) "
            "OR (tipo = 'al_hogar' AND prestatario_id IS NULL "
            "AND ((prestamista_id IS NOT NULL) <> (contraparte_nombre IS NOT NULL))) "
            "OR (tipo = 'del_hogar' AND prestamista_id IS NULL "
            "AND ((prestatario_id IS NOT NULL) <> (contraparte_nombre IS NOT NULL)))",
            name="partes_coherentes",
        ),
        CheckConstraint("importe > 0", name="importe_positivo"),
        CheckConstraint("total_a_pagar >= importe", name="total_no_menor_al_importe"),
        CheckConstraint("numero_cuotas BETWEEN 1 AND 360", name="cuotas_validas"),
    )


class Cuota(IdUuidMixin, Base):
    """Cuota programada de un préstamo."""

    __tablename__ = "installments"

    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    loan_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_installments_id_hogar"),
        UniqueConstraint("loan_id", "numero", name="uq_installments_prestamo_numero"),
        ForeignKeyConstraint(
            ["loan_id", "household_id"],
            ["loans.id", "loans.household_id"],
            ondelete="RESTRICT",
            name="fk_installments_prestamo_hogar_loans",
        ),
        CheckConstraint("importe > 0", name="importe_positivo"),
        CheckConstraint("numero > 0", name="numero_positivo"),
    )


class PagoCuota(IdUuidMixin, Base):
    """Vínculo entre una cuota y el movimiento real que la pagó (total o parcialmente)."""

    __tablename__ = "installment_payments"

    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    installment_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["installment_id", "household_id"],
            ["installments.id", "installments.household_id"],
            ondelete="RESTRICT",
            name="fk_installment_payments_cuota_hogar_installments",
        ),
        ForeignKeyConstraint(
            ["transaction_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_installment_payments_movimiento_hogar_transactions",
        ),
        UniqueConstraint("transaction_id", name="uq_installment_payments_movimiento"),
        CheckConstraint("importe > 0", name="importe_positivo"),
    )