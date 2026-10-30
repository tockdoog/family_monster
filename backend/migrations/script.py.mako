## backend/migrations/script.py.mako
## Plantilla que Alembic usa para generar cada nueva migración.
## Recuerde escribir al inicio de cada migración generada su ruta y una línea que explique su propósito.
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Identificadores de la migración (los gestiona Alembic).
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Aplica los cambios de esquema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revierte los cambios de esquema."""
    ${downgrades if downgrades else "pass"}
