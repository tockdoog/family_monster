# backend/migrations/versions/20261016_0002_cuentas_movimientos_auditoria.py
# Migración 0002: cuentas, libro de movimientos, auditoría y triggers de protección del historial.
"""cuentas movimientos auditoria

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 00:51:49.589250
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Identificadores de la migración (los gestiona Alembic).
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica los cambios de esquema."""
    # Requisito previo: (id, hogar) único en integrantes para las llaves compuestas de cuentas y movimientos.
    op.create_unique_constraint('uq_members_id_hogar', 'members', ['id', 'household_id'])
    # Auditoría: bitácora permanente de acciones sensibles.
    op.create_table('audit_logs',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('usuario_id', sa.Uuid(), nullable=False),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('entidad', sa.String(length=40), nullable=False),
    sa.Column('entidad_id', sa.Uuid(), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=True),
    sa.Column('detalle', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_audit_logs_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], name=op.f('fk_audit_logs_usuario_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs'))
    )
    op.create_index('ix_audit_logs_hogar_fecha', 'audit_logs', ['household_id', 'creado_en'], unique=False)
    # Cuentas: el saldo se deriva de los movimientos, no se almacena.
    op.create_table('accounts',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('propietario_id', sa.Uuid(), nullable=True),
    sa.Column('saldo_inicial', sa.Numeric(precision=14, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(tipo = 'personal') = (propietario_id IS NOT NULL)", name=op.f('ck_accounts_propietario_solo_personal')),
    sa.CheckConstraint("tipo IN ('efectivo', 'banco', 'personal', 'otra')", name=op.f('ck_accounts_tipo_valido')),
    sa.CheckConstraint('length(trim(nombre)) > 0', name=op.f('ck_accounts_nombre_no_vacio')),
    sa.CheckConstraint('saldo_inicial >= 0', name=op.f('ck_accounts_saldo_inicial_no_negativo')),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_accounts_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['propietario_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_accounts_propietario_hogar_members', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_accounts')),
    sa.UniqueConstraint('id', 'household_id', name='uq_accounts_id_hogar')
    )
    op.create_index('uq_accounts_hogar_nombre', 'accounts', ['household_id', sa.literal_column('lower(nombre)')], unique=True)
    # Cabecera de movimientos del libro financiero.
    op.create_table('transactions',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('estado', sa.String(length=20), server_default='confirmada', nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('descripcion', sa.String(length=500), nullable=False),
    sa.Column('registrado_por', sa.Uuid(), nullable=False),
    sa.Column('pagador_id', sa.Uuid(), nullable=True),
    sa.Column('beneficiario_id', sa.Uuid(), nullable=True),
    sa.Column('clave_idempotencia', sa.String(length=80), nullable=False),
    sa.Column('huella', sa.String(length=64), nullable=False),
    sa.Column('reversa_de_id', sa.Uuid(), nullable=True),
    sa.Column('motivo', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(tipo = 'reversion') = (reversa_de_id IS NOT NULL)", name=op.f('ck_transactions_reversion_coherente')),
    sa.CheckConstraint("estado IN ('confirmada', 'revertida')", name=op.f('ck_transactions_estado_valido')),
    sa.CheckConstraint("tipo <> 'reversion' OR (estado = 'confirmada' AND length(trim(coalesce(motivo, ''))) >= 5)", name=op.f('ck_transactions_reversion_con_motivo')),
    sa.CheckConstraint("tipo IN ('ingreso', 'gasto', 'transferencia', 'reversion')", name=op.f('ck_transactions_tipo_valido')),
    sa.CheckConstraint('length(trim(descripcion)) > 0', name=op.f('ck_transactions_descripcion_no_vacia')),
    sa.ForeignKeyConstraint(['beneficiario_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_transactions_beneficiario_hogar_members', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_transactions_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['pagador_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_transactions_pagador_hogar_members', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['registrado_por'], ['users.id'], name=op.f('fk_transactions_registrado_por_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reversa_de_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_transactions_reversa_hogar_transactions', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transactions')),
    sa.UniqueConstraint('household_id', 'clave_idempotencia', name='uq_transactions_hogar_clave'),
    sa.UniqueConstraint('id', 'household_id', name='uq_transactions_id_hogar'),
    sa.UniqueConstraint('reversa_de_id', name='uq_transactions_reversa_de')
    )
    op.create_index('ix_transactions_hogar_fecha', 'transactions', ['household_id', 'fecha'], unique=False)
    # Líneas con signo por cuenta: positivo entra dinero, negativo sale.
    op.create_table('transaction_lines',
    sa.Column('transaction_id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('account_id', sa.Uuid(), nullable=False),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('importe <> 0', name=op.f('ck_transaction_lines_importe_distinto_de_cero')),
    sa.ForeignKeyConstraint(['account_id', 'household_id'], ['accounts.id', 'accounts.household_id'], name='fk_transaction_lines_cuenta_hogar_accounts', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['transaction_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_transaction_lines_movimiento_hogar_transactions', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transaction_lines'))
    )
    op.create_index(op.f('ix_transaction_lines_account_id'), 'transaction_lines', ['account_id'], unique=False)
    op.create_index(op.f('ix_transaction_lines_transaction_id'), 'transaction_lines', ['transaction_id'], unique=False)

    # Trigger 1: el historial financiero no se borra ni se edita (regla 7). La única modificación
    # permitida es marcar un movimiento 'confirmada' como 'revertida' sin tocar ningún otro dato.
    op.execute("""
        CREATE FUNCTION proteger_historial_financiero() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Los registros de % no se pueden borrar.', TG_TABLE_NAME
                    USING ERRCODE = 'restrict_violation';
            END IF;
            -- Se lee 'estado' vía to_jsonb porque esta función es compartida por varias tablas y
            -- no todas tienen esa columna (OLD.estado fallaría en transaction_lines y audit_logs).
            IF TG_TABLE_NAME = 'transactions' THEN
                IF to_jsonb(OLD)->>'estado' = 'confirmada' AND to_jsonb(NEW)->>'estado' = 'revertida'
                   AND (to_jsonb(NEW) - 'estado' - 'actualizado_en')
                       = (to_jsonb(OLD) - 'estado' - 'actualizado_en') THEN
                    RETURN NEW;
                END IF;
            END IF;
            RAISE EXCEPTION 'Los registros de % no se pueden modificar.', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
    """)
    for tabla in ("transactions", "transaction_lines", "audit_logs"):
        op.execute(
            f"CREATE TRIGGER trg_proteger_{tabla} BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION proteger_historial_financiero()"
        )

    # Trigger 2: una transferencia debe sumar cero (lo que sale de una cuenta entra en otra).
    # Se verifica al confirmar la transacción (DEFERRED), cuando ya existen todas sus líneas.
    op.execute("""
        CREATE FUNCTION verificar_transferencia_balanceada() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            tipo_movimiento text;
            suma numeric;
        BEGIN
            SELECT tipo INTO tipo_movimiento FROM transactions WHERE id = NEW.transaction_id;
            IF tipo_movimiento = 'transferencia' THEN
                SELECT COALESCE(SUM(importe), 0) INTO suma
                FROM transaction_lines WHERE transaction_id = NEW.transaction_id;
                IF suma <> 0 THEN
                    RAISE EXCEPTION 'La transferencia % no está balanceada (suma %).',
                        NEW.transaction_id, suma USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NULL;
        END;
        $$;
    """)
    op.execute(
        "CREATE CONSTRAINT TRIGGER trg_transferencia_balanceada AFTER INSERT ON transaction_lines "
        "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION verificar_transferencia_balanceada()"
    )


def downgrade() -> None:
    """Revierte los cambios de esquema."""
    # Primero se eliminan las funciones de protección (los triggers caen con sus tablas).
    op.execute('DROP TRIGGER IF EXISTS trg_transferencia_balanceada ON transaction_lines')
    op.execute('DROP FUNCTION IF EXISTS verificar_transferencia_balanceada()')
    op.drop_index(op.f('ix_transaction_lines_transaction_id'), table_name='transaction_lines')
    op.drop_index(op.f('ix_transaction_lines_account_id'), table_name='transaction_lines')
    op.drop_table('transaction_lines')
    op.drop_index('ix_transactions_hogar_fecha', table_name='transactions')
    op.drop_table('transactions')
    op.drop_index('uq_accounts_hogar_nombre', table_name='accounts')
    op.drop_table('accounts')
    op.drop_index('ix_audit_logs_hogar_fecha', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.execute('DROP FUNCTION IF EXISTS proteger_historial_financiero()')
    # Por último, la restricción de integrantes que usaban las llaves compuestas.
    op.drop_constraint('uq_members_id_hogar', 'members', type_='unique')