# backend/migrations/versions/20261014_0001_esquema_inicial.py
# Migración inicial: usuarios, intentos de login, hogares, membresías e integrantes.
"""esquema inicial identidad hogares integrantes

Revision ID: 0001
Revises: 
Create Date: 2026-10-15 04:47:27.186820
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de la migración (los gestiona Alembic).
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica los cambios de esquema."""
    # Hogares: unidad que aísla los datos financieros (solo COP en la versión 1).
    op.create_table('households',
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('moneda', sa.String(length=3), server_default='COP', nullable=False),
    sa.Column('zona_horaria', sa.String(length=64), server_default='America/Bogota', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("moneda = 'COP'", name=op.f('ck_households_moneda_soportada')),
    sa.CheckConstraint('length(trim(nombre)) > 0', name=op.f('ck_households_nombre_no_vacio')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_households'))
    )
    # Intentos de login por hash de correo, para bloquear la fuerza bruta.
    op.create_table('login_attempts',
    sa.Column('clave', sa.String(length=64), nullable=False),
    sa.Column('intentos', sa.Integer(), nullable=False),
    sa.Column('primer_intento_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('bloqueado_hasta', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('intentos >= 0', name=op.f('ck_login_attempts_intentos_no_negativos')),
    sa.PrimaryKeyConstraint('clave', name=op.f('pk_login_attempts'))
    )
    # Usuarios con acceso a la aplicación (solo hash Argon2id, correo en minúsculas).
    op.create_table('users',
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('nombre_completo', sa.String(length=120), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_minusculas')),
    sa.CheckConstraint('length(trim(nombre_completo)) > 0', name=op.f('ck_users_nombre_no_vacio')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    # Membresías: relacionan usuario con hogar y rol; un hogar por usuario en la versión 1.
    op.create_table('memberships',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('rol', sa.String(length=20), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("rol IN ('admin', 'miembro')", name=op.f('ck_memberships_rol_valido')),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_memberships_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_memberships_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_memberships')),
    sa.UniqueConstraint('user_id', 'household_id', name='uq_memberships_usuario_hogar'),
    sa.UniqueConstraint('user_id', name='uq_memberships_un_hogar_por_usuario')
    )
    op.create_index(op.f('ix_memberships_household_id'), 'memberships', ['household_id'], unique=False)
    # Integrantes financieros; la llave compuesta obliga a que el usuario vinculado sea del mismo hogar.
    op.create_table('members',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=True),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(trim(nombre)) > 0', name=op.f('ck_members_nombre_no_vacio')),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_members_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id', 'household_id'], ['memberships.user_id', 'memberships.household_id'], name='fk_members_usuario_hogar_memberships', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_members')),
    sa.UniqueConstraint('user_id', name=op.f('uq_members_user_id'))
    )
    # Nombre único por hogar sin distinguir mayúsculas.
    op.create_index('uq_members_hogar_nombre', 'members', ['household_id', sa.literal_column('lower(nombre)')], unique=True)


def downgrade() -> None:
    """Revierte los cambios de esquema."""
    # Se eliminan en orden inverso a la creación para respetar las llaves foráneas.
    op.drop_index('uq_members_hogar_nombre', table_name='members')
    op.drop_table('members')
    op.drop_index(op.f('ix_memberships_household_id'), table_name='memberships')
    op.drop_table('memberships')
    op.drop_table('users')
    op.drop_table('login_attempts')
    op.drop_table('households')