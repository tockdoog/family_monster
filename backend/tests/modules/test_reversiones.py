# backend/tests/modules/test_reversiones.py
# Pruebas de reversiones: el historial se conserva, los saldos se restauran y todo es trazable.

from decimal import Decimal

import pytest

from tests.ayudas import crear_cuenta, gasto, ingreso, nueva_clave, revertir, saldos, transferencia

MOVS = "/api/v1/transactions"
ADMIN = "ana@example.com"


@pytest.fixture
def admin(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Administrador autenticado de un hogar."""
    crear_hogar()
    return iniciar_sesion(nuevo_cliente(), ADMIN)


def test_revertir_un_gasto_restaura_el_saldo_y_conserva_el_historial(admin):
    """El original NO se borra: queda 'revertida' y aparece junto a su reversión."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    original = gasto(admin, cuenta["id"], 120000)
    assert saldos(admin)["Efectivo"] == Decimal("380000")

    respuesta = revertir(admin, original["id"], "Se registró dos veces")
    assert respuesta.status_code == 201
    reversion = respuesta.json()
    assert reversion["tipo"] == "reversion" and reversion["estado"] == "confirmada"
    assert reversion["reversa_de_id"] == original["id"]
    assert reversion["motivo"] == "Se registró dos veces"
    assert reversion["lineas"] == [{"cuenta_id": cuenta["id"], "importe": "120000"}]
    assert saldos(admin)["Efectivo"] == Decimal("500000")

    historial = {m["id"]: m for m in admin.get(MOVS).json()["items"]}
    assert historial[original["id"]]["estado"] == "revertida"
    assert historial[original["id"]]["lineas"][0]["importe"] == "-120000"  # sin alterar
    assert reversion["id"] in historial


def test_revertir_una_transferencia_restaura_ambas_cuentas(admin):
    """Se revierten las dos líneas: cada cuenta vuelve a su saldo anterior."""
    banco = crear_cuenta(admin, "Banco", saldo=1000000, tipo="banco")
    efectivo = crear_cuenta(admin, "Efectivo")
    mov = transferencia(admin, banco["id"], efectivo["id"], 300000)
    assert revertir(admin, mov["id"]).status_code == 201
    assert saldos(admin) == {"Banco": Decimal("1000000"), "Efectivo": Decimal("0")}


def test_un_movimiento_solo_se_revierte_una_vez(admin):
    """La segunda reversión del mismo movimiento se rechaza (409)."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=10000)
    mov = gasto(admin, cuenta["id"], 1000)
    assert revertir(admin, mov["id"]).status_code == 201
    segunda = revertir(admin, mov["id"])
    assert segunda.status_code == 409
    assert saldos(admin)["Efectivo"] == Decimal("10000")


def test_una_reversion_no_se_puede_revertir(admin):
    """Revertir una reversión se rechaza: la corrección correcta es registrar un movimiento nuevo."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=10000)
    reversion = revertir(admin, gasto(admin, cuenta["id"], 1000)["id"]).json()
    assert revertir(admin, reversion["id"]).status_code == 422


def test_el_motivo_es_obligatorio_y_con_sentido(admin):
    """Sin motivo, o con uno de menos de 5 caracteres, no se revierte."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=10000)
    mov = gasto(admin, cuenta["id"], 1000)
    url = f"{MOVS}/{mov['id']}/reverse"
    cabecera = {"Idempotency-Key": nueva_clave()}
    assert admin.post(url, json={}, headers=cabecera).status_code == 422
    assert revertir(admin, mov["id"], motivo="  ab  ").status_code == 422
    assert saldos(admin)["Efectivo"] == Decimal("9000")


def test_no_se_puede_revertir_un_ingreso_cuyo_dinero_ya_se_gasto(admin):
    """Ninguna cuenta queda en negativo, ni siquiera por una reversión: primero hay que reponer saldo."""
    cuenta = crear_cuenta(admin, "Efectivo")
    entrada = ingreso(admin, cuenta["id"], 100000)
    gasto(admin, cuenta["id"], 80000)

    rechazo = revertir(admin, entrada["id"], "El ingreso era de otra cuenta")
    assert rechazo.status_code == 422
    assert "saldo negativo" in rechazo.json()["error"]["mensaje"]
    # No cambió nada: saldo igual, el ingreso sigue confirmado y no se creó ninguna reversión.
    assert saldos(admin)["Efectivo"] == Decimal("20000")
    assert admin.get(MOVS, params={"tipo": "reversion"}).json()["total"] == 0
    assert admin.get(MOVS, params={"estado": "revertida"}).json()["total"] == 0

    # Al reponer el saldo, la reversión ya es posible y el saldo queda en cero (nunca negativo).
    ingreso(admin, cuenta["id"], 80000)
    assert revertir(admin, entrada["id"], "El ingreso era de otra cuenta").status_code == 201
    assert saldos(admin)["Efectivo"] == Decimal("0")


def test_revertir_una_transferencia_se_rechaza_si_el_destino_ya_gasto_el_dinero(admin):
    """En una transferencia la cuenta de destino también debe poder devolver el dinero."""
    banco = crear_cuenta(admin, "Banco", saldo=500000, tipo="banco")
    efectivo = crear_cuenta(admin, "Efectivo")
    mov = transferencia(admin, banco["id"], efectivo["id"], 200000)
    gasto(admin, efectivo["id"], 150000)
    assert revertir(admin, mov["id"]).status_code == 422
    assert saldos(admin) == {"Banco": Decimal("300000"), "Efectivo": Decimal("50000")}


def test_permisos_de_la_reversion(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro no puede revertir (403) y sin sesión tampoco (401)."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    mov = ingreso(admin, crear_cuenta(admin, "Efectivo")["id"], 5000)
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert revertir(marta, mov["id"]).status_code == 403
    assert revertir(cliente, mov["id"]).status_code == 401
    assert admin.get(MOVS).json()["total"] == 1


def test_no_se_puede_revertir_un_movimiento_de_otro_hogar(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: el movimiento de otro hogar 'no existe' para quien intenta revertirlo."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    mov_a = ingreso(admin_a, crear_cuenta(admin_a, "Cuenta A")["id"], 9000)
    assert revertir(admin_b, mov_a["id"]).status_code == 404
    assert saldos(admin_a)["Cuenta A"] == Decimal("9000")
    assert admin_a.get(MOVS).json()["items"][0]["estado"] == "confirmada"


def test_movimiento_inexistente_o_id_invalido(admin):
    """Un id desconocido da 404 y uno mal formado da 422."""
    import uuid

    assert revertir(admin, str(uuid.uuid4())).status_code == 404
    assert revertir(admin, "no-es-uuid").status_code == 422