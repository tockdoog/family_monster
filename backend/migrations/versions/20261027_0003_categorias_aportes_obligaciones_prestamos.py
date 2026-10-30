# backend/migrations/versions/20261027_0003_categorias_aportes_obligaciones_prestamos.py
# Migración 0003: categorías, reglas de aporte y repartos, obligaciones, préstamos y cuotas,
# nuevos tipos de movimiento y protección del historial en las tablas nuevas.
"""categorias aportes obligaciones prestamos

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 03:14:17.675723
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de la migración (los gestiona Alembic).
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica los cambios de esquema."""
    # Categorías de gasto configurables por hogar.
    op.create_table('categories',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=60), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(trim(nombre)) > 0', name=op.f('ck_categories_nombre_no_vacio')),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_categories_household_id_households'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('id', 'household_id', name='uq_categories_id_hogar')
    )
    op.create_index('uq_categories_hogar_nombre', 'categories', ['household_id', sa.literal_column('lower(nombre)')], unique=True)
    # Reglas de aporte: cómo se reparte un gasto, con vigencia.
    op.create_table('contribution_rules',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('categoria_id', sa.Uuid(), nullable=True),
    sa.Column('vigente_desde', sa.Date(), nullable=False),
    sa.Column('vigente_hasta', sa.Date(), nullable=True),
    sa.Column('creado_por', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(trim(nombre)) > 0', name=op.f('ck_contribution_rules_nombre_no_vacio')),
    sa.CheckConstraint('vigente_hasta IS NULL OR vigente_hasta >= vigente_desde', name=op.f('ck_contribution_rules_vigencia_coherente')),
    sa.ForeignKeyConstraint(['categoria_id', 'household_id'], ['categories.id', 'categories.household_id'], name='fk_contribution_rules_categoria_hogar_categories', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['creado_por'], ['users.id'], name=op.f('fk_contribution_rules_creado_por_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_contribution_rules_household_id_households'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contribution_rules')),
    sa.UniqueConstraint('id', 'household_id', name='uq_contribution_rules_id_hogar')
    )
    op.create_index('uq_contribution_rules_alcance_desde', 'contribution_rules', ['household_id', sa.literal_column("coalesce(categoria_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'vigente_desde'], unique=True)
    # Parte de cada integrante dentro de una regla (porcentaje, parte igual o importe fijo).
    op.create_table('contribution_rule_items',
    sa.Column('rule_id', sa.Uuid(), nullable=False),
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('valor', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint("tipo <> 'porcentaje' OR valor <= 100", name=op.f('ck_contribution_rule_items_porcentaje_maximo_100')),
    sa.CheckConstraint("tipo IN ('porcentaje', 'parte', 'fijo')", name=op.f('ck_contribution_rule_items_tipo_valido')),
    sa.CheckConstraint('valor > 0', name=op.f('ck_contribution_rule_items_valor_positivo')),
    sa.ForeignKeyConstraint(['member_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_contribution_rule_items_integrante_hogar_members', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['rule_id', 'household_id'], ['contribution_rules.id', 'contribution_rules.household_id'], name='fk_contribution_rule_items_regla_hogar_contribution_rules', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contribution_rule_items')),
    sa.UniqueConstraint('rule_id', 'member_id', name='uq_contribution_rule_items_regla_integrante')
    )
    # Obligaciones (facturas, servicios, deudas); su saldo se deriva de los pagos.
    op.create_table('obligations',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('descripcion', sa.String(length=300), nullable=False),
    sa.Column('categoria_id', sa.Uuid(), nullable=False),
    sa.Column('importe_original', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('fecha_creacion', sa.Date(), nullable=False),
    sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
    sa.Column('acreedor', sa.String(length=120), nullable=False),
    sa.Column('responsable_id', sa.Uuid(), nullable=True),
    sa.Column('anulada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_anulacion', sa.Text(), nullable=True),
    sa.Column('anulada_por', sa.Uuid(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(anulada_en IS NULL) = (motivo_anulacion IS NULL) AND (anulada_en IS NULL) = (anulada_por IS NULL)', name=op.f('ck_obligations_anulacion_coherente')),
    sa.CheckConstraint('fecha_vencimiento >= fecha_creacion', name=op.f('ck_obligations_vencimiento_coherente')),
    sa.CheckConstraint('importe_original > 0', name=op.f('ck_obligations_importe_positivo')),
    sa.CheckConstraint('length(trim(acreedor)) > 0', name=op.f('ck_obligations_acreedor_no_vacio')),
    sa.CheckConstraint('length(trim(descripcion)) > 0', name=op.f('ck_obligations_descripcion_no_vacia')),
    sa.ForeignKeyConstraint(['anulada_por'], ['users.id'], name=op.f('fk_obligations_anulada_por_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['categoria_id', 'household_id'], ['categories.id', 'categories.household_id'], name='fk_obligations_categoria_hogar_categories', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_obligations_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['responsable_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_obligations_responsable_hogar_members', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_obligations')),
    sa.UniqueConstraint('id', 'household_id', name='uq_obligations_id_hogar')
    )
    # Foto histórica de lo que le correspondió pagar a cada integrante de cada gasto.
    op.create_table('contribution_shares',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('transaction_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('rule_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=12), nullable=False),
    sa.Column('valor', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('importe >= 0', name=op.f('ck_contribution_shares_importe_no_negativo')),
    sa.ForeignKeyConstraint(['member_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_contribution_shares_integrante_hogar_members', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['rule_id', 'household_id'], ['contribution_rules.id', 'contribution_rules.household_id'], name='fk_contribution_shares_regla_hogar_contribution_rules', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['transaction_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_contribution_shares_movimiento_hogar_transactions', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contribution_shares')),
    sa.UniqueConstraint('transaction_id', 'member_id', name='uq_contribution_shares_movimiento_integrante')
    )
    op.create_index(op.f('ix_contribution_shares_member_id'), 'contribution_shares', ['member_id'], unique=False)
    op.create_index(op.f('ix_contribution_shares_transaction_id'), 'contribution_shares', ['transaction_id'], unique=False)
    # Préstamos entre integrantes, al hogar y del hogar.
    op.create_table('loans',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('prestamista_id', sa.Uuid(), nullable=True),
    sa.Column('prestatario_id', sa.Uuid(), nullable=True),
    sa.Column('contraparte_nombre', sa.String(length=120), nullable=True),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_a_pagar', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('numero_cuotas', sa.Integer(), nullable=False),
    sa.Column('condiciones', sa.Text(), nullable=True),
    sa.Column('desembolso_transaction_id', sa.Uuid(), nullable=False),
    sa.Column('creado_por', sa.Uuid(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(tipo = 'entre_integrantes' AND prestamista_id IS NOT NULL AND prestatario_id IS NOT NULL AND contraparte_nombre IS NULL AND prestamista_id <> prestatario_id) OR (tipo = 'al_hogar' AND prestatario_id IS NULL AND ((prestamista_id IS NOT NULL) <> (contraparte_nombre IS NOT NULL))) OR (tipo = 'del_hogar' AND prestamista_id IS NULL AND ((prestatario_id IS NOT NULL) <> (contraparte_nombre IS NOT NULL)))", name=op.f('ck_loans_partes_coherentes')),
    sa.CheckConstraint("tipo IN ('entre_integrantes', 'al_hogar', 'del_hogar')", name=op.f('ck_loans_tipo_valido')),
    sa.CheckConstraint('importe > 0', name=op.f('ck_loans_importe_positivo')),
    sa.CheckConstraint('numero_cuotas BETWEEN 1 AND 360', name=op.f('ck_loans_cuotas_validas')),
    sa.CheckConstraint('total_a_pagar >= importe', name=op.f('ck_loans_total_no_menor_al_importe')),
    sa.ForeignKeyConstraint(['creado_por'], ['users.id'], name=op.f('fk_loans_creado_por_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['desembolso_transaction_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_loans_desembolso_hogar_transactions', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_loans_household_id_households'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['prestamista_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_loans_prestamista_hogar_members', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['prestatario_id', 'household_id'], ['members.id', 'members.household_id'], name='fk_loans_prestatario_hogar_members', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_loans')),
    sa.UniqueConstraint('desembolso_transaction_id', name='uq_loans_desembolso'),
    sa.UniqueConstraint('id', 'household_id', name='uq_loans_id_hogar')
    )
    # Pagos de obligaciones, siempre ligados a un movimiento real del libro.
    op.create_table('obligation_payments',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('obligation_id', sa.Uuid(), nullable=False),
    sa.Column('transaction_id', sa.Uuid(), nullable=False),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('importe > 0', name=op.f('ck_obligation_payments_importe_positivo')),
    sa.ForeignKeyConstraint(['obligation_id', 'household_id'], ['obligations.id', 'obligations.household_id'], name='fk_obligation_payments_obligacion_hogar_obligations', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['transaction_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_obligation_payments_movimiento_hogar_transactions', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_obligation_payments')),
    sa.UniqueConstraint('transaction_id', name='uq_obligation_payments_movimiento')
    )
    op.create_index(op.f('ix_obligation_payments_obligation_id'), 'obligation_payments', ['obligation_id'], unique=False)
    # Cuotas programadas de cada préstamo.
    op.create_table('installments',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('loan_id', sa.Uuid(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('importe > 0', name=op.f('ck_installments_importe_positivo')),
    sa.CheckConstraint('numero > 0', name=op.f('ck_installments_numero_positivo')),
    sa.ForeignKeyConstraint(['loan_id', 'household_id'], ['loans.id', 'loans.household_id'], name='fk_installments_prestamo_hogar_loans', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_installments')),
    sa.UniqueConstraint('id', 'household_id', name='uq_installments_id_hogar'),
    sa.UniqueConstraint('loan_id', 'numero', name='uq_installments_prestamo_numero')
    )
    op.create_index(op.f('ix_installments_loan_id'), 'installments', ['loan_id'], unique=False)
    # Pagos de cuotas, siempre ligados a un movimiento real del libro.
    op.create_table('installment_payments',
    sa.Column('household_id', sa.Uuid(), nullable=False),
    sa.Column('installment_id', sa.Uuid(), nullable=False),
    sa.Column('transaction_id', sa.Uuid(), nullable=False),
    sa.Column('importe', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.CheckConstraint('importe > 0', name=op.f('ck_installment_payments_importe_positivo')),
    sa.ForeignKeyConstraint(['installment_id', 'household_id'], ['installments.id', 'installments.household_id'], name='fk_installment_payments_cuota_hogar_installments', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['transaction_id', 'household_id'], ['transactions.id', 'transactions.household_id'], name='fk_installment_payments_movimiento_hogar_transactions', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_installment_payments')),
    sa.UniqueConstraint('transaction_id', name='uq_installment_payments_movimiento')
    )
    op.create_index(op.f('ix_installment_payments_installment_id'), 'installment_payments', ['installment_id'], unique=False)
    # Los movimientos pueden clasificarse por categoría (del mismo hogar).
    op.add_column('transactions', sa.Column('categoria_id', sa.Uuid(), nullable=True))
    op.create_foreign_key('fk_transactions_categoria_hogar_categories', 'transactions', 'categories', ['categoria_id', 'household_id'], ['id', 'household_id'], ondelete='RESTRICT')

    # Nuevos tipos de movimiento: Alembic no detecta cambios en CHECK existentes, se reemplaza a mano.
    op.drop_constraint(op.f('ck_transactions_tipo_valido'), 'transactions', type_='check')
    op.create_check_constraint(
        'tipo_valido',
        'transactions',
        "tipo IN ('ingreso', 'gasto', 'transferencia', 'reversion', 'aporte', 'reembolso', "
        "'pago_obligacion', 'desembolso_prestamo', 'pago_cuota')",
    )

    # El historial de repartos y pagos tampoco se borra ni se edita (misma protección de la migración 0002).
    for tabla in ("contribution_shares", "contribution_rule_items", "obligation_payments", "installment_payments"):
        op.execute(
            f"CREATE TRIGGER trg_proteger_{tabla} BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION proteger_historial_financiero()"
        )

    # Un reembolso mueve dinero entre dos cuentas, así que también debe sumar cero.
    op.execute("""
        CREATE OR REPLACE FUNCTION verificar_transferencia_balanceada() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            tipo_movimiento text;
            suma numeric;
        BEGIN
            SELECT tipo INTO tipo_movimiento FROM transactions WHERE id = NEW.transaction_id;
            IF tipo_movimiento IN ('transferencia', 'reembolso') THEN
                SELECT COALESCE(SUM(importe), 0) INTO suma
                FROM transaction_lines WHERE transaction_id = NEW.transaction_id;
                IF suma <> 0 THEN
                    RAISE EXCEPTION 'El movimiento % no está balanceado (suma %).',
                        NEW.transaction_id, suma USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NULL;
        END;
        $$;
    """)

    # Los hogares que ya existían reciben las categorías iniciales (los nuevos las reciben al crearse).
    op.execute("""
        INSERT INTO categories (id, household_id, nombre)
        SELECT gen_random_uuid(), h.id, c.nombre
        FROM households h
        CROSS JOIN (VALUES ('Agua'), ('Energía'), ('Gas'), ('Internet'), ('Mercado'), ('Arriendo'),
                           ('Reparaciones'), ('Transporte'), ('Salud'), ('Préstamos'), ('Otros')) AS c(nombre)
    """)


def downgrade() -> None:
    """Revierte los cambios de esquema.

    Nota: solo es posible si no existen movimientos de los tipos nuevos (aporte, reembolso,
    pago_obligacion, desembolso_prestamo, pago_cuota); en ese caso la base lo rechaza a propósito.
    """
    # Se restaura la verificación original (solo transferencias) y la restricción de tipos.
    op.execute("""
        CREATE OR REPLACE FUNCTION verificar_transferencia_balanceada() RETURNS trigger
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
    op.drop_constraint(op.f('ck_transactions_tipo_valido'), 'transactions', type_='check')
    op.create_check_constraint(
        'tipo_valido',
        'transactions',
        "tipo IN ('ingreso', 'gasto', 'transferencia', 'reversion')",
    )
    # Se eliminan las tablas nuevas en orden inverso (sus triggers caen con ellas).
    op.drop_constraint('fk_transactions_categoria_hogar_categories', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'categoria_id')
    op.drop_index(op.f('ix_installment_payments_installment_id'), table_name='installment_payments')
    op.drop_table('installment_payments')
    op.drop_index(op.f('ix_installments_loan_id'), table_name='installments')
    op.drop_table('installments')
    op.drop_index(op.f('ix_obligation_payments_obligation_id'), table_name='obligation_payments')
    op.drop_table('obligation_payments')
    op.drop_table('loans')
    op.drop_index(op.f('ix_contribution_shares_transaction_id'), table_name='contribution_shares')
    op.drop_index(op.f('ix_contribution_shares_member_id'), table_name='contribution_shares')
    op.drop_table('contribution_shares')
    op.drop_table('obligations')
    op.drop_table('contribution_rule_items')
    op.drop_index('uq_contribution_rules_alcance_desde', table_name='contribution_rules')
    op.drop_table('contribution_rules')
    op.drop_index('uq_categories_hogar_nombre', table_name='categories')
    op.drop_table('categories')