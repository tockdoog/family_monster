# backend/tests/modules/test_integridad_financiera_bd.py
# Barreras de la base de datos: aunque el código fallara, el libro financiero no se puede corromper.

import random
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.modules.accounts.models import Cuenta
from app.modules.transactions.models import LineaMovimiento, Movimiento
from tests.ayudas import crear_cuenta, gasto, ingreso, registrar, revertir, saldos, transferencia

ADMIN = "ana@example.com"


@pytest.fixture
def entorno(crear_hogar, sesion):
    """Hogar con un usuario administrador y dos cuentas, creados directamente en la base."""
    hogar = crear_hogar()
    usuario_id = sesion.execute(text("SELECT id FROM users")).scalar_one()
    cuentas = []
    for nombre in ("Efectivo", "Banco"):
        cuenta = Cuenta(household_id=hogar.id, nombre=nombre, tipo="efectivo", saldo_inicial=Decimal(0))
        sesion.add(cuenta)
        cuentas.append(cuenta)
    sesion.commit()
    return {"hogar": hogar, "usuario_id": usuario_id, "cuentas": cuentas}


def _movimiento(sesion, entorno, tipo="gasto", **extra) -> Movimiento:
    """Inserta una cabecera de movimiento directamente en la base."""
    movimiento = Movimiento(
        household_id=entorno["hogar"].id,
        tipo=tipo,
        fecha=date(2026, 10, 1),
        descripcion="Prueba directa",
        registrado_por=entorno["usuario_id"],
        clave_idempotencia=f"clave-{uuid.uuid4().hex}",
        huella="h" * 64,
        **extra,
    )
    sesion.add(movimiento)
    sesion.flush()
    return movimiento


def _linea(sesion, entorno, movimiento, cuenta, importe) -> LineaMovimiento:
    """Inserta una línea de movimiento directamente en la base."""
    linea = LineaMovimiento(
        transaction_id=movimiento.id, household_id=entorno["hogar"].id, account_id=cuenta.id, importe=Decimal(importe)
    )
    sesion.add(linea)
    sesion.flush()
    return linea


def test_no_se_puede_borrar_ni_editar_el_historial(sesion, entorno):
    """Regla 7: borrar o editar movimientos, líneas o auditoría es imposible incluso con SQL directo."""
    efectivo = entorno["cuentas"][0]
    mov = _movimiento(sesion, entorno)
    linea = _linea(sesion, entorno, mov, efectivo, "-1000")
    sesion.commit()

    sentencias = [
        ("DELETE FROM transactions", {}),
        ("DELETE FROM transaction_lines", {}),
        ("DELETE FROM audit_logs", {}),
        ("UPDATE transactions SET descripcion = 'alterada'", {}),
        ("UPDATE transactions SET fecha = '2020-01-01'", {}),
        ("UPDATE transaction_lines SET importe = -1", {}),
        ("UPDATE transaction_lines SET account_id = account_id", {}),
        ("UPDATE audit_logs SET accion = 'otra'", {}),
    ]
    for sql, params in sentencias:
        with pytest.raises(IntegrityError):
            sesion.execute(text(sql), params)
        sesion.rollback()
    # Nada cambió.
    assert sesion.execute(text("SELECT descripcion FROM transactions")).scalar_one() == "Prueba directa"
    assert sesion.execute(text("SELECT importe FROM transaction_lines")).scalar_one() == Decimal("-1000")
    assert linea.id is not None


def test_unica_modificacion_permitida_es_marcar_como_revertida(sesion, entorno):
    """'confirmada' -> 'revertida' sí; volver atrás o cambiar otro dato a la vez, no."""
    mov = _movimiento(sesion, entorno)
    sesion.commit()
    with pytest.raises(IntegrityError):  # cambia estado Y descripción a la vez
        sesion.execute(text("UPDATE transactions SET estado = 'revertida', descripcion = 'x'"))
    sesion.rollback()
    sesion.execute(text("UPDATE transactions SET estado = 'revertida'"))
    sesion.commit()
    with pytest.raises(IntegrityError):  # no se puede "des-revertir"
        sesion.execute(text("UPDATE transactions SET estado = 'confirmada'"))
    sesion.rollback()
    assert sesion.execute(text("SELECT estado FROM transactions WHERE id = :i"), {"i": mov.id}).scalar_one() == "revertida"


def test_transferencia_desbalanceada_no_se_puede_confirmar(sesion, entorno):
    """Regla 5 en la base: una transferencia cuyas líneas no suman cero falla al confirmar."""
    efectivo, banco = entorno["cuentas"]
    mov = _movimiento(sesion, entorno, tipo="transferencia")
    _linea(sesion, entorno, mov, efectivo, "-1000")
    _linea(sesion, entorno, mov, banco, "900")  # faltan 100 pesos
    with pytest.raises(DBAPIError):
        sesion.commit()
    sesion.rollback()
    assert sesion.execute(text("SELECT count(*) FROM transactions")).scalar_one() == 0


def test_transferencia_balanceada_si_se_confirma(sesion, entorno):
    """Una transferencia que suma cero se acepta."""
    efectivo, banco = entorno["cuentas"]
    mov = _movimiento(sesion, entorno, tipo="transferencia")
    _linea(sesion, entorno, mov, efectivo, "-1000")
    _linea(sesion, entorno, mov, banco, "1000")
    sesion.commit()
    assert sesion.execute(text("SELECT count(*) FROM transaction_lines")).scalar_one() == 2


def test_una_linea_no_puede_apuntar_a_una_cuenta_de_otro_hogar(sesion, entorno, crear_hogar):
    """La llave compuesta (cuenta, hogar) impide mezclar hogares en el libro."""
    otro = crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    cuenta_ajena = Cuenta(household_id=otro.id, nombre="Ajena", tipo="efectivo", saldo_inicial=Decimal(0))
    sesion.add(cuenta_ajena)
    sesion.commit()
    mov = _movimiento(sesion, entorno)
    with pytest.raises(IntegrityError):
        _linea(sesion, entorno, mov, cuenta_ajena, "-500")
    sesion.rollback()


def test_restricciones_del_libro(sesion, entorno):
    """Importe cero, reversión sin motivo/original y doble reversión son rechazados por la base."""
    efectivo = entorno["cuentas"][0]
    original = _movimiento(sesion, entorno)
    _linea(sesion, entorno, original, efectivo, "-100")
    sesion.commit()

    mov = _movimiento(sesion, entorno)
    with pytest.raises(IntegrityError):
        _linea(sesion, entorno, mov, efectivo, "0")
    sesion.rollback()

    with pytest.raises(IntegrityError):  # reversión sin motivo
        _movimiento(sesion, entorno, tipo="reversion", reversa_de_id=original.id)
    sesion.rollback()
    with pytest.raises(IntegrityError):  # reversión sin original
        _movimiento(sesion, entorno, tipo="reversion", motivo="Motivo válido")
    sesion.rollback()
    with pytest.raises(IntegrityError):  # movimiento normal que dice revertir a otro
        _movimiento(sesion, entorno, tipo="gasto", reversa_de_id=original.id)
    sesion.rollback()

    _movimiento(sesion, entorno, tipo="reversion", reversa_de_id=original.id, motivo="Motivo válido")
    sesion.commit()
    with pytest.raises(IntegrityError):  # un original no se revierte dos veces
        _movimiento(sesion, entorno, tipo="reversion", reversa_de_id=original.id, motivo="Otro motivo")
    sesion.rollback()


def test_idempotencia_a_nivel_de_base_de_datos(sesion, entorno):
    """Aunque el código fallara, la base impide dos movimientos con la misma clave en un hogar."""
    _movimiento(sesion, entorno)
    duplicado = Movimiento(
        household_id=entorno["hogar"].id, tipo="gasto", fecha=date(2026, 10, 1), descripcion="dup",
        registrado_por=entorno["usuario_id"], clave_idempotencia="repetida-00000001", huella="h" * 64,
    )
    original = Movimiento(
        household_id=entorno["hogar"].id, tipo="gasto", fecha=date(2026, 10, 1), descripcion="orig",
        registrado_por=entorno["usuario_id"], clave_idempotencia="repetida-00000001", huella="h" * 64,
    )
    sesion.add(original)
    sesion.flush()
    sesion.add(duplicado)
    with pytest.raises(IntegrityError):
        sesion.flush()
    sesion.rollback()


def test_el_libro_coincide_con_un_modelo_independiente(crear_hogar, nuevo_cliente, iniciar_sesion, sesion):
    """Regla 10: tras 60 operaciones aleatorias (con reversiones), cada saldo coincide con un cálculo
    independiente hecho en la prueba, y también con la suma directa de líneas en SQL."""
    azar = random.Random(7)
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    inicial = {"Efectivo": 800000, "Banco": 1500000, "Ahorros": 300000}
    ids = {n: crear_cuenta(admin, n, saldo=s)["id"] for n, s in inicial.items()}
    esperado = {n: Decimal(s) for n, s in inicial.items()}
    por_id = {v: k for k, v in ids.items()}
    revertibles: list[tuple[str, dict[str, Decimal]]] = []
    cuenta = {"reversiones": 0, "rechazos": 0, "transferencias": 0, "rechazos_reversion": 0}

    for _ in range(60):
        accion = azar.choice(["ingreso", "ingreso", "gasto", "gasto", "transferencia", "transferencia", "revertir", "revertir"])
        importe = azar.randint(1, 2000) * 1000
        a, b = azar.sample(list(ids), 2)
        if accion == "ingreso":
            m = ingreso(admin, ids[a], importe)
            esperado[a] += importe
            revertibles.append((m["id"], {a: Decimal(importe)}))
        elif accion == "gasto":
            r = registrar(admin, tipo="gasto", importe=importe, cuenta_origen_id=ids[a])
            if esperado[a] - importe >= 0:
                assert r.status_code == 201
                esperado[a] -= importe
                revertibles.append((r.json()["id"], {a: Decimal(-importe)}))
            else:
                assert r.status_code == 422  # saldo insuficiente: el modelo también lo prevé
                cuenta["rechazos"] += 1
        elif accion == "transferencia":
            r = registrar(admin, tipo="transferencia", importe=importe, cuenta_origen_id=ids[a], cuenta_destino_id=ids[b])
            if esperado[a] - importe >= 0:
                assert r.status_code == 201
                esperado[a] -= importe
                esperado[b] += importe
                revertibles.append((r.json()["id"], {a: Decimal(-importe), b: Decimal(importe)}))
                cuenta["transferencias"] += 1
            else:
                assert r.status_code == 422
                cuenta["rechazos"] += 1
        elif revertibles:
            posicion = azar.randrange(len(revertibles))
            mov_id, efecto = revertibles[posicion]
            # El modelo prevé el resultado: se rechaza si alguna cuenta quedaría en negativo.
            quedaria_negativa = any(esperado[n] - delta < 0 for n, delta in efecto.items())
            respuesta = revertir(admin, mov_id, "Corrección aleatoria")
            if quedaria_negativa:
                assert respuesta.status_code == 422
                cuenta["rechazos_reversion"] += 1
            else:
                assert respuesta.status_code == 201
                revertibles.pop(posicion)
                for nombre, delta in efecto.items():
                    esperado[nombre] -= delta
                cuenta["reversiones"] += 1
        # Invariante global: jamás hay una cuenta con saldo negativo.
        assert all(v >= 0 for v in esperado.values())

    assert saldos(admin) == esperado

    # Contraste con SQL directo: saldo inicial + suma de todas las líneas de movimientos con efecto.
    filas = sesion.execute(text("""
        SELECT a.id, a.saldo_inicial + COALESCE(SUM(l.importe), 0)
        FROM accounts a
        LEFT JOIN transaction_lines l ON l.account_id = a.id
        LEFT JOIN transactions t ON t.id = l.transaction_id AND t.estado IN ('confirmada', 'revertida')
        GROUP BY a.id, a.saldo_inicial
    """)).all()
    assert {por_id[str(f[0])]: f[1] for f in filas} == esperado
    # La prueba solo vale si la secuencia realmente ejercitó reversiones, rechazos y transferencias.
    assert cuenta["reversiones"] >= 5 and cuenta["rechazos"] >= 3 and cuenta["transferencias"] >= 5, cuenta
    assert cuenta["rechazos_reversion"] >= 1, cuenta  # también se ejerció el rechazo de reversiones