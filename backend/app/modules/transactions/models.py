# backend/app/modules/transactions/models.py
# Libro de movimientos. Cada movimiento tiene líneas con signo por cuenta: el saldo de una cuenta
# es su saldo inicial más la suma de sus líneas. Las filas confirmadas nunca se borran ni se
# editan (lo garantizan triggers en la base): se corrigen con una reversión trazable.

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin, TipoDinero


class TipoMovimiento(StrEnum):
    """Clases de movimiento. Cada concepto financiero tiene su propio tipo (regla 2)."""

    INGRESO = "ingreso"
    GASTO = "gasto"
    TRANSFERENCIA = "transferencia"
    REVERSION = "reversion"
    # Dinero que un integrante entrega al fondo común (no es un ingreso ordinario).
    APORTE = "aporte"
    # Devolución del fondo común a un integrante que pagó con su propio dinero.
    REEMBOLSO = "reembolso"
    # Pago (total o parcial) de una obligación: factura, servicio o deuda.
    PAGO_OBLIGACION = "pago_obligacion"
    # Entrega del dinero de un préstamo (no es ingreso ni gasto).
    DESEMBOLSO_PRESTAMO = "desembolso_prestamo"
    # Pago de una cuota de préstamo (no es gasto ordinario).
    PAGO_CUOTA = "pago_cuota"


class EstadoMovimiento(StrEnum):
    """'revertida' marca al movimiento original que ya fue contrarrestado por una reversión."""

    CONFIRMADA = "confirmada"
    REVERTIDA = "revertida"


# Movimientos que son gasto del hogar: se reparten entre los integrantes y suman en "gastos".
TIPOS_GASTO_HOGAR = (TipoMovimiento.GASTO.value, TipoMovimiento.PAGO_OBLIGACION.value)

# Ambos estados afectan el saldo: el original y su reversión se anulan entre sí.
ESTADOS_CON_EFECTO = (EstadoMovimiento.CONFIRMADA.value, EstadoMovimiento.REVERTIDA.value)


class Movimiento(IdUuidMixin, MarcaTiempoMixin, Base):
    """Cabecera de un movimiento financiero del hogar."""

    __tablename__ = "transactions"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="confirmada")
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(500), nullable=False)
    registrado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    pagador_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    beneficiario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Categoría opcional (ingresos y gastos); las obligaciones la heredan de la obligación.
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Protección contra duplicados: una clave por operación y hogar.
    clave_idempotencia: Mapped[str] = mapped_column(String(80), nullable=False)
    huella: Mapped[str] = mapped_column(String(64), nullable=False)
    # Solo en reversiones: movimiento original que se contrarresta y motivo obligatorio.
    reversa_de_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_transactions_id_hogar"),
        UniqueConstraint("household_id", "clave_idempotencia", name="uq_transactions_hogar_clave"),
        # Un movimiento solo puede revertirse una vez.
        UniqueConstraint("reversa_de_id", name="uq_transactions_reversa_de"),
        # Pagador, beneficiario y movimiento original deben pertenecer al mismo hogar.
        ForeignKeyConstraint(
            ["pagador_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_transactions_pagador_hogar_members",
        ),
        ForeignKeyConstraint(
            ["beneficiario_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_transactions_beneficiario_hogar_members",
        ),
        ForeignKeyConstraint(
            ["categoria_id", "household_id"],
            ["categories.id", "categories.household_id"],
            ondelete="RESTRICT",
            name="fk_transactions_categoria_hogar_categories",
        ),
        ForeignKeyConstraint(
            ["reversa_de_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_transactions_reversa_hogar_transactions",
        ),
        CheckConstraint(
            "tipo IN ('ingreso', 'gasto', 'transferencia', 'reversion', 'aporte', 'reembolso', "
            "'pago_obligacion', 'desembolso_prestamo', 'pago_cuota')",
            name="tipo_valido",
        ),
        CheckConstraint("estado IN ('confirmada', 'revertida')", name="estado_valido"),
        # Reversión <=> apunta a un original.
        CheckConstraint("(tipo = 'reversion') = (reversa_de_id IS NOT NULL)", name="reversion_coherente"),
        # Toda reversión exige motivo y una reversión no puede revertirse a su vez.
        CheckConstraint(
            "tipo <> 'reversion' OR (estado = 'confirmada' AND length(trim(coalesce(motivo, ''))) >= 5)",
            name="reversion_con_motivo",
        ),
        CheckConstraint("length(trim(descripcion)) > 0", name="descripcion_no_vacia"),
        Index("ix_transactions_hogar_fecha", "household_id", "fecha"),
    )


class LineaMovimiento(IdUuidMixin, Base):
    """Efecto de un movimiento sobre una cuenta: positivo entra dinero, negativo sale."""

    __tablename__ = "transaction_lines"

    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # La línea, su movimiento y su cuenta deben pertenecer al MISMO hogar.
        ForeignKeyConstraint(
            ["transaction_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_transaction_lines_movimiento_hogar_transactions",
        ),
        ForeignKeyConstraint(
            ["account_id", "household_id"],
            ["accounts.id", "accounts.household_id"],
            ondelete="RESTRICT",
            name="fk_transaction_lines_cuenta_hogar_accounts",
        ),
        CheckConstraint("importe <> 0", name="importe_distinto_de_cero"),
    )