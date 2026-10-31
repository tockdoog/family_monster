# backend/tests/test_integridad_modulos_bd.py
# Barreras de integridad en la base de datos para repartos, pagos, préstamos, obligaciones y
# movimientos: comprueba que PostgreSQL rechaza por sí mismo cambios imposibles, incluso con SQL directo.

import uuid  # Genera claves de idempotencia únicas para los movimientos creados a mano en las pruebas.
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.transactions.models import LineaMovimiento, Movimiento
from tests.ayudas import (
    crear_cuenta,
    crear_integrante,
    gasto,
    integrantes,
    nueva_clave,
    obligacion_ok,
    pagar_obligacion,
    regla_ok,
)

ADMIN = "ana@example.com"


@pytest.fixture
def datos(crear_hogar, nuevo_cliente, iniciar_sesion, sesion):
    """Hogar con una regla, un gasto repartido, una obligación pagada y un préstamo con un pago."""
    hogar = crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    crear_integrante(admin, "Luis")
    ids = integrantes(admin)
    comun = crear_cuenta(admin, "Fondo común", saldo=1000000, tipo="banco")
    regla_ok(admin, [{"integrante_id": i, "tipo": "parte"} for i in ids.values()])
    gasto(admin, comun["id"], 100000)
    obl = obligacion_ok(admin, importe=50000)
    pagar_obligacion(admin, obl["id"], 50000, comun["id"])
    prestamo = admin.post(
        "/api/v1/loans",
        json={"tipo": "al_hogar", "contraparte_nombre": "Banco", "importe": 100000, "numero_cuotas": 1, "cuenta_destino_id": comun["id"]},
        headers={"Idempotency-Key": nueva_clave()},
    ).json()
    admin.post(
        f"/api/v1/loans/{prestamo['id']}/payments",
        json={"cuota_numero": 1, "importe": 40000, "cuenta_origen_id": comun["id"]},
        headers={"Idempotency-Key": nueva_clave()},
    )
    return {"hogar": hogar, "usuario_id": sesion.execute(text("SELECT id FROM users")).scalar_one(), "comun": comun["id"]}


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM contribution_shares",
        "UPDATE contribution_shares SET importe = 1",
        "DELETE FROM contribution_rule_items",
        "UPDATE contribution_rule_items SET valor = 5",
        "DELETE FROM obligation_payments",
        "UPDATE obligation_payments SET importe = 1",
        "DELETE FROM installment_payments",
        "UPDATE installment_payments SET importe = 1",
    ],
)
def test_repartos_y_pagos_no_se_borran_ni_se_editan(datos, sesion, sql):
    """La foto de cada reparto y el vínculo de cada pago son permanentes, incluso con SQL directo."""
    with pytest.raises(IntegrityError):
        sesion.execute(text(sql))
    sesion.rollback()
    for tabla in ("contribution_shares", "contribution_rule_items", "obligation_payments", "installment_payments"):
        assert sesion.execute(text(f"SELECT count(*) FROM {tabla}")).scalar_one() > 0


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE loans SET tipo = 'entre_integrantes'",                    # partes incoherentes con el tipo
        "UPDATE loans SET total_a_pagar = 1",                              # total menor que lo prestado
        "UPDATE loans SET numero_cuotas = 0",
        "UPDATE obligations SET anulada_en = now()",                       # anulada sin motivo ni responsable
        "UPDATE obligations SET importe_original = 0",
        "UPDATE obligations SET fecha_vencimiento = fecha_creacion - 1",
        "UPDATE contribution_rules SET vigente_hasta = vigente_desde - 1",
        "UPDATE installments SET importe = -5",
        "UPDATE categories SET nombre = '   '",
    ],
)
def test_restricciones_de_negocio_en_la_base(datos, sesion, sql):
    """Estados y montos imposibles son rechazados por la propia base de datos."""
    with pytest.raises(IntegrityError):
        sesion.execute(text(sql))
    sesion.rollback()


def test_no_hay_dos_reglas_del_mismo_alcance_que_empiecen_el_mismo_dia(datos, sesion):
    """El índice único de vigencia impide reglas duplicadas aunque el código no lo validara."""
    with pytest.raises(IntegrityError):
        sesion.execute(text("""
            INSERT INTO contribution_rules (id, household_id, nombre, categoria_id, vigente_desde, creado_por)
            SELECT gen_random_uuid(), household_id, 'duplicada', categoria_id, vigente_desde, creado_por
            FROM contribution_rules LIMIT 1
        """))
    sesion.rollback()


def test_un_movimiento_no_puede_pagar_dos_obligaciones(datos, sesion):
    """Cada pago está atado a un único movimiento real (restricción única)."""
    with pytest.raises(IntegrityError):
        sesion.execute(text("""
            INSERT INTO obligation_payments (id, household_id, obligation_id, transaction_id, importe)
            SELECT gen_random_uuid(), household_id, obligation_id, transaction_id, 1 FROM obligation_payments LIMIT 1
        """))
    sesion.rollback()


def test_un_reembolso_desbalanceado_no_se_puede_confirmar(datos, sesion):
    """El trigger exige que un reembolso sume cero (sale de una cuenta, entra en otra)."""
    otra = sesion.execute(
        text("INSERT INTO accounts (id, household_id, nombre, tipo, saldo_inicial) "
             "VALUES (gen_random_uuid(), :h, 'Auxiliar', 'efectivo', 0) RETURNING id"),
        {"h": datos["hogar"].id},
    ).scalar_one()
    mov = Movimiento(
        household_id=datos["hogar"].id, tipo="reembolso", fecha=date(2026, 10, 1), descripcion="Descuadrado",
        registrado_por=datos["usuario_id"], clave_idempotencia=f"clave-{uuid.uuid4().hex}", huella="h" * 64,
    )
    sesion.add(mov)
    sesion.flush()
    for cuenta, importe in ((datos["comun"], "-1000"), (otra, "900")):
        sesion.add(LineaMovimiento(transaction_id=mov.id, household_id=datos["hogar"].id, account_id=cuenta, importe=Decimal(importe)))
    with pytest.raises(DBAPIError):
        sesion.commit()
    sesion.rollback()


def test_tipos_de_movimiento_desconocidos_se_rechazan(datos, sesion):
    """Solo existen los tipos definidos: un tipo inventado es imposible."""
    sesion.add(Movimiento(
        household_id=datos["hogar"].id, tipo="inventado", fecha=date(2026, 10, 1), descripcion="x",
        registrado_por=datos["usuario_id"], clave_idempotencia=f"clave-{uuid.uuid4().hex}", huella="h" * 64,
    ))
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()


def test_las_categorias_no_se_pueden_borrar_si_tienen_uso(datos, sesion):
    """Borrado restringido: una categoría usada por una obligación no desaparece."""
    with pytest.raises(IntegrityError):
        sesion.execute(text("DELETE FROM categories WHERE id IN (SELECT categoria_id FROM obligations)"))
    sesion.rollback()