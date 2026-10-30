# backend/app/db/base.py
# Base declarativa de todos los modelos, convención de nombres para restricciones
# (necesaria para migraciones Alembic estables) y mezclas comunes.

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Numeric, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nombres predecibles para índices, llaves y CHECK: permiten migrar y revertir sin ambigüedad.
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Tipo único para dinero: NUMERIC(14,2) en PostgreSQL y Decimal en Python. Nunca float.
TipoDinero = Numeric(precision=14, scale=2, asdecimal=True)


class Base(DeclarativeBase):
    """Clase base de la que heredan todos los modelos."""

    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


class IdUuidMixin:
    """Llave primaria UUID: no es adivinable ni enumerable desde el cliente."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class MarcaTiempoMixin:
    """Fechas de creación y última modificación, siempre con zona horaria (UTC)."""

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )