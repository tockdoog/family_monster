# backend/tests/modules/test_movimientos.py
# Pruebas de ingresos, gastos y transferencias: reglas, validaciones, permisos y aislamiento.

from datetime import timedelta
from decimal import Decimal

import pytest

from app.shared.fechas import hoy_colombia
from tests.ayudas import crear_cuenta, gasto, ingreso, nueva_clave, registrar, registrar_ok, saldos, transferencia

MOVS = "/api/v1/transactions"
ADMIN = "ana@example.com"


@pytest.fixture
def admin(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Administrador autenticado de un hogar."""
    crear_hogar()
    return iniciar_sesion(nuevo_cliente(), ADMIN)


def test_ingreso_aumenta_el_saldo(admin):
    """Un ingreso suma a la cuenta de destino y queda confirmado."""
    cuenta = crear_cuenta(admin, "Efectivo")
    mov = ingreso(admin, cuenta["id"], 300000)
    assert mov["tipo"] == "ingreso" and mov["estado"] == "confirmada"
    assert mov["importe"] == "300000"
    assert mov["lineas"] == [{"cuenta_id": cuenta["id"], "importe": "300000"}]
    assert saldos(admin)["Efectivo"] == Decimal("300000")


def test_gasto_disminuye_el_saldo(admin):
    """Un gasto resta de la cuenta de origen."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    mov = gasto(admin, cuenta["id"], 120000)
    assert mov["lineas"][0]["importe"] == "-120000"
    assert saldos(admin)["Efectivo"] == Decimal("380000")


def test_transferencia_mueve_el_dinero_sin_crear_ingresos_ni_gastos(admin):
    """Regla 5: sale de una cuenta, entra en la otra, y no cuenta como ingreso ni gasto."""
    banco = crear_cuenta(admin, "Banco", saldo=1000000, tipo="banco")
    efectivo = crear_cuenta(admin, "Efectivo")
    mov = transferencia(admin, banco["id"], efectivo["id"], 400000)
    assert sorted(l["importe"] for l in mov["lineas"]) == ["-400000", "400000"]
    assert mov["importe"] == "400000"

    estado = saldos(admin)
    assert estado["Banco"] == Decimal("600000") and estado["Efectivo"] == Decimal("400000")
    # El dinero total del hogar no cambia.
    assert sum(estado.values()) == Decimal("1000000")
    # No hay ni un ingreso ni un gasto registrados.
    assert admin.get(MOVS, params={"tipo": "ingreso"}).json()["total"] == 0
    assert admin.get(MOVS, params={"tipo": "gasto"}).json()["total"] == 0
    assert admin.get(MOVS, params={"tipo": "transferencia"}).json()["total"] == 1


def test_saldo_insuficiente_se_rechaza_sin_dejar_rastro(admin):
    """No se puede gastar ni transferir más de lo que hay; el saldo y el libro no cambian."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    otra = crear_cuenta(admin, "Banco", tipo="banco")
    r1 = registrar(admin, tipo="gasto", importe=100001, cuenta_origen_id=cuenta["id"])
    r2 = registrar(admin, tipo="transferencia", importe=100001, cuenta_origen_id=cuenta["id"], cuenta_destino_id=otra["id"])
    assert r1.status_code == r2.status_code == 422
    assert "Saldo insuficiente" in r1.json()["error"]["mensaje"]
    assert saldos(admin)["Efectivo"] == Decimal("100000")
    assert admin.get(MOVS).json()["total"] == 0
    # Gastar exactamente todo el saldo sí está permitido.
    assert registrar(admin, tipo="gasto", importe=100000, cuenta_origen_id=cuenta["id"]).status_code == 201


@pytest.mark.parametrize(
    "datos",
    [
        {"tipo": "ingreso", "origen": True},                    # ingreso con cuenta de origen
        {"tipo": "ingreso"},                                    # ingreso sin destino
        {"tipo": "gasto", "destino": True},                     # gasto con destino
        {"tipo": "gasto"},                                      # gasto sin origen
        {"tipo": "transferencia", "origen": True},              # transferencia sin destino
        {"tipo": "transferencia", "origen": True, "destino_igual": True},  # misma cuenta
    ],
)
def test_combinaciones_de_cuentas_invalidas(admin, datos):
    """Cada tipo de movimiento exige exactamente las cuentas que le corresponden."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000)
    otra = crear_cuenta(admin, "Banco", tipo="banco", saldo=1000)
    cuerpo = {"tipo": datos["tipo"], "importe": 500}
    if datos.get("origen"):
        cuerpo["cuenta_origen_id"] = cuenta["id"]
    if datos.get("destino"):
        cuerpo["cuenta_destino_id"] = otra["id"]
    if datos.get("destino_igual"):
        cuerpo["cuenta_destino_id"] = cuenta["id"]
    assert registrar(admin, **cuerpo).status_code == 422


@pytest.mark.parametrize("importe", [0, -500, "100.50", "abc", None])
def test_importes_invalidos_se_rechazan(admin, importe):
    """Cero, negativos, centavos y no numéricos nunca se aceptan."""
    cuenta = crear_cuenta(admin, "Efectivo")
    assert registrar(admin, tipo="ingreso", importe=importe, cuenta_destino_id=cuenta["id"]).status_code == 422


def test_fechas(admin):
    """Hoy y el pasado se aceptan; el futuro no. Sin fecha se usa la de Colombia."""
    cuenta = crear_cuenta(admin, "Efectivo")
    hoy = hoy_colombia()
    futuro = registrar(admin, tipo="ingreso", importe=1000, cuenta_destino_id=cuenta["id"], fecha=str(hoy + timedelta(days=1)))
    assert futuro.status_code == 422
    pasado = registrar_ok(admin, tipo="ingreso", importe=1000, cuenta_destino_id=cuenta["id"], fecha=str(hoy - timedelta(days=40)))
    sin_fecha = registrar_ok(admin, tipo="ingreso", importe=1000, cuenta_destino_id=cuenta["id"])
    assert pasado["fecha"] == str(hoy - timedelta(days=40))
    assert sin_fecha["fecha"] == str(hoy)


def test_cuenta_inexistente_inactiva_o_de_otro_hogar(admin, sesion, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Cuentas que no existen en el hogar dan 404; las inactivas se rechazan con 422."""
    import uuid

    from sqlalchemy import text

    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000)
    assert registrar(admin, tipo="ingreso", importe=10, cuenta_destino_id=str(uuid.uuid4())).status_code == 404

    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    ajena = crear_cuenta(admin_b, "Cuenta de B", saldo=5000)
    assert registrar(admin, tipo="ingreso", importe=10, cuenta_destino_id=ajena["id"]).status_code == 404
    assert registrar(admin, tipo="gasto", importe=10, cuenta_origen_id=ajena["id"]).status_code == 404

    sesion.execute(text("UPDATE accounts SET activa = false WHERE id = :i"), {"i": cuenta["id"]})
    sesion.commit()
    inactiva = registrar(admin, tipo="ingreso", importe=10, cuenta_destino_id=cuenta["id"])
    assert inactiva.status_code == 422 and "inactiva" in inactiva.json()["error"]["mensaje"]


def test_pagador_de_otro_hogar_se_rechaza(admin, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Los integrantes referenciados deben ser del hogar de la sesión."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000)
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    ajeno = admin_b.get("/api/v1/members").json()[0]["id"]
    assert registrar(admin, tipo="gasto", importe=10, cuenta_origen_id=cuenta["id"], pagador_id=ajeno).status_code == 404
    propio = admin.get("/api/v1/members").json()[0]["id"]
    ok = registrar_ok(admin, tipo="gasto", importe=10, cuenta_origen_id=cuenta["id"], pagador_id=propio)
    assert ok["pagador_id"] == propio


def test_permisos_miembro_y_sin_sesion(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro no puede registrar movimientos (403) y sin sesión tampoco (401)."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    cuenta = crear_cuenta(admin, "Efectivo")
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    cuerpo = {"tipo": "ingreso", "importe": 1000, "descripcion": "x", "cuenta_destino_id": cuenta["id"]}
    cabecera = {"Idempotency-Key": nueva_clave()}
    assert marta.post(MOVS, json=cuerpo, headers=cabecera).status_code == 403
    assert cliente.post(MOVS, json=cuerpo, headers=cabecera).status_code == 401
    assert marta.get(MOVS).status_code == 200  # consultar sí puede


def test_la_clave_de_idempotencia_es_obligatoria_y_valida(admin):
    """Sin cabecera, o con una clave corta o con caracteres raros, se rechaza."""
    cuenta = crear_cuenta(admin, "Efectivo")
    cuerpo = {"tipo": "ingreso", "importe": 1000, "descripcion": "x", "cuenta_destino_id": cuenta["id"]}
    assert admin.post(MOVS, json=cuerpo).status_code == 422
    for mala in ("corta", "con espacios no vale", "a" * 81, "raro;drop"):
        assert admin.post(MOVS, json=cuerpo, headers={"Idempotency-Key": mala}).status_code == 422


def test_campos_desconocidos_y_descripcion_vacia_se_rechazan(admin):
    """Contrato estricto: sin campos extra ni descripciones en blanco."""
    cuenta = crear_cuenta(admin, "Efectivo")
    base = {"tipo": "ingreso", "importe": 1000, "cuenta_destino_id": cuenta["id"]}
    assert admin.post(MOVS, json={**base, "descripcion": "x", "estado": "revertida"}, headers={"Idempotency-Key": nueva_clave()}).status_code == 422
    assert admin.post(MOVS, json={**base, "descripcion": "   "}, headers={"Idempotency-Key": nueva_clave()}).status_code == 422


def test_listado_con_filtros_y_paginacion(admin):
    """Filtra por tipo, cuenta y fechas, y pagina con total."""
    efectivo = crear_cuenta(admin, "Efectivo", saldo=1000000)
    banco = crear_cuenta(admin, "Banco", tipo="banco")
    for i in range(5):
        gasto(admin, efectivo["id"], 1000 * (i + 1))
    ingreso(admin, banco["id"], 50000)
    transferencia(admin, efectivo["id"], banco["id"], 20000)

    todos = admin.get(MOVS).json()
    assert todos["total"] == 7
    pagina = admin.get(MOVS, params={"limite": 3, "desplazamiento": 3}).json()
    assert len(pagina["items"]) == 3 and pagina["total"] == 7
    assert admin.get(MOVS, params={"tipo": "gasto"}).json()["total"] == 5
    assert admin.get(MOVS, params={"cuenta_id": banco["id"]}).json()["total"] == 2
    hoy = str(hoy_colombia())
    assert admin.get(MOVS, params={"desde": hoy, "hasta": hoy}).json()["total"] == 7
    assert admin.get(MOVS, params={"hasta": str(hoy_colombia() - timedelta(days=1))}).json()["total"] == 0
    assert admin.get(MOVS, params={"limite": 1000}).status_code == 422
    assert admin.get(MOVS, params={"tipo": "inventado"}).status_code == 422


def test_un_hogar_no_ve_los_movimientos_de_otro(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: el listado y las cuentas de cada hogar son independientes."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    ingreso(admin_a, crear_cuenta(admin_a, "Cuenta A")["id"], 7000)
    assert admin_b.get(MOVS).json()["total"] == 0
    assert admin_a.get(MOVS).json()["total"] == 1


def test_el_importe_del_movimiento_es_el_dinero_movido_en_todos_los_tipos(admin):
    """Un gasto (solo sale dinero) no puede mostrar importe 0: el importe es lo que entra o lo que sale."""
    efectivo = crear_cuenta(admin, "Efectivo", saldo=500000)
    banco = crear_cuenta(admin, "Banco", tipo="banco")
    assert gasto(admin, efectivo["id"], 120000)["importe"] == "120000"
    assert ingreso(admin, efectivo["id"], 80000)["importe"] == "80000"
    assert transferencia(admin, efectivo["id"], banco["id"], 50000)["importe"] == "50000"
    listado = admin.get(MOVS).json()["items"]
    assert sorted(m["importe"] for m in listado) == ["120000", "50000", "80000"]
    assert all(int(m["importe"]) > 0 for m in listado)


def test_el_importe_de_una_reversion_es_el_del_movimiento_original(admin):
    """La reversión de un gasto (entra dinero) y la de un ingreso (sale dinero) muestran el mismo importe."""
    from tests.ayudas import revertir

    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    g = gasto(admin, cuenta["id"], 70000)
    assert revertir(admin, g["id"]).json()["importe"] == "70000"
    i = ingreso(admin, cuenta["id"], 30000)
    assert revertir(admin, i["id"]).json()["importe"] == "30000"