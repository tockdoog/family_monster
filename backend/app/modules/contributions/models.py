# backend/app/modules/contributions/models.py
# Reglas de aporte (cómo se reparte un gasto entre los integrantes) y la "foto" histórica de
# cada reparto aplicado. Un cambio de regla nunca altera los repartos ya calculados.

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin, TipoDinero


class ReglaAporte(IdUuidMixin, MarcaTiempoMixin, Base):
    """Regla de reparto con vigencia. Sin categoría es la regla general del hogar."""

    __tablename__ = "contribution_rules"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # Si tiene categoría, solo aplica a gastos de esa categoría y prevalece sobre la regla general.
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)
    # Se completa cuando una regla posterior de su mismo alcance la reemplaza.
    vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    creado_por: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("id", "household_id", name="uq_contribution_rules_id_hogar"),
        ForeignKeyConstraint(
            ["categoria_id", "household_id"],
            ["categories.id", "categories.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_rules_categoria_hogar_categories",
        ),
        CheckConstraint(
            "vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia_coherente"
        ),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        # No puede haber dos reglas del mismo alcance que empiecen el mismo día.
        Index(
            "uq_contribution_rules_alcance_desde",
            "household_id",
            text("coalesce(categoria_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            "vigente_desde",
            unique=True,
        ),
    )


class ItemReglaAporte(IdUuidMixin, Base):
    """Parte de un integrante dentro de una regla (inmutable: para cambiar se crea otra regla)."""

    __tablename__ = "contribution_rule_items"

    rule_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # porcentaje: valor entre 0 y 100 | parte: parte igual (valor 1) | fijo: pesos COP.
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    valor: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["rule_id", "household_id"],
            ["contribution_rules.id", "contribution_rules.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_rule_items_regla_hogar_contribution_rules",
        ),
        ForeignKeyConstraint(
            ["member_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_rule_items_integrante_hogar_members",
        ),
        UniqueConstraint("rule_id", "member_id", name="uq_contribution_rule_items_regla_integrante"),
        CheckConstraint("tipo IN ('porcentaje', 'parte', 'fijo')", name="tipo_valido"),
        CheckConstraint("valor > 0", name="valor_positivo"),
        CheckConstraint("tipo <> 'porcentaje' OR valor <= 100", name="porcentaje_maximo_100"),
    )


class ParteAporte(IdUuidMixin, Base):
    """Lo que le corresponde pagar a un integrante de un gasto concreto (obligación esperada).

    Guarda una copia de la regla y del valor aplicados en ese momento, de modo que el reparto
    histórico se pueda reconstruir aunque la regla cambie después.
    """

    __tablename__ = "contribution_shares"

    household_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    rule_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    # Copia (snapshot) de los parámetros usados.
    tipo: Mapped[str] = mapped_column(String(12), nullable=False)
    valor: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    importe: Mapped[Decimal] = mapped_column(TipoDinero, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["transaction_id", "household_id"],
            ["transactions.id", "transactions.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_shares_movimiento_hogar_transactions",
        ),
        ForeignKeyConstraint(
            ["member_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_shares_integrante_hogar_members",
        ),
        ForeignKeyConstraint(
            ["rule_id", "household_id"],
            ["contribution_rules.id", "contribution_rules.household_id"],
            ondelete="RESTRICT",
            name="fk_contribution_shares_regla_hogar_contribution_rules",
        ),
        UniqueConstraint("transaction_id", "member_id", name="uq_contribution_shares_movimiento_integrante"),
        CheckConstraint("importe >= 0", name="importe_no_negativo"),
    )