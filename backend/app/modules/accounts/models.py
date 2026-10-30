# backend/app/modules/accounts/models.py
# Cuentas o fondos del hogar. El saldo NO se guarda: se deriva del saldo inicial más los
# movimientos confirmados, así nunca puede contradecirse con el historial.

import uuid
from decimal import Decimal
from enum import StrEnum

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

from app.db.base import Base, IdUuidMixin, MarcaTiempoMixin, TipoDinero


class TipoCuenta(StrEnum):
    """Tipos de cuenta. 'personal' es dinero de un integrante; los demás son fondo común."""

    EFECTIVO = "efectivo"
    BANCO = "banco"
    PERSONAL = "personal"
    OTRA = "otra"


class Cuenta(IdUuidMixin, MarcaTiempoMixin, Base):
    """Cuenta de dinero del hogar (efectivo, banco, fondo personal u otra)."""

    __tablename__ = "accounts"

    household_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("households.id", ondelete="RESTRICT"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    # Solo las cuentas personales tienen propietario.
    propietario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Inmutable: fija el punto de partida del saldo derivado.
    saldo_inicial: Mapped[Decimal] = mapped_column(
        TipoDinero, nullable=False, server_default=text("0")
    )
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())

    __table_args__ = (
        # Permite que las líneas de movimiento referencien (cuenta, hogar).
        UniqueConstraint("id", "household_id", name="uq_accounts_id_hogar"),
        # El propietario debe ser un integrante de ESTE mismo hogar.
        ForeignKeyConstraint(
            ["propietario_id", "household_id"],
            ["members.id", "members.household_id"],
            ondelete="RESTRICT",
            name="fk_accounts_propietario_hogar_members",
        ),
        CheckConstraint(
            "tipo IN ('efectivo', 'banco', 'personal', 'otra')", name="tipo_valido"
        ),
        # Cuenta personal <=> tiene propietario.
        CheckConstraint(
            "(tipo = 'personal') = (propietario_id IS NOT NULL)", name="propietario_solo_personal"
        ),
        CheckConstraint("saldo_inicial >= 0", name="saldo_inicial_no_negativo"),
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        # No se repiten nombres de cuenta dentro del hogar (sin distinguir mayúsculas).
        Index("uq_accounts_hogar_nombre", "household_id", text("lower(nombre)"), unique=True),
    )