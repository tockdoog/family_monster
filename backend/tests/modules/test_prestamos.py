# backend/tests/modules/test_prestamos.py
# Pruebas de préstamos y cuotas: desembolso, cuotas exactas, pagos, estados, reversiones y aislamiento.

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.modules.loans.service import estado_de_cuota
from app.shared.fechas import hoy_colombia, sumar_meses
from tests.ayudas import (
    crear_cuenta,
    crear_integrante,
    crear_regla,
    gasto,
    integrantes,
    nueva_clave,
    regla_ok,
    revertir,
)

LOANS = "/api/v1/loans"
ADMIN = "ana@example.com"


def _crear(cliente, clave=None, **extra):
    """Crea un préstamo (devuelve la respuesta sin validar el estado)."""
    cuerpo = {"importe": 1200000, "numero_cuotas": 12, **extra}
    return cliente.post(LOANS, json=cuerpo, headers={"Idempotency-Key": clave or nueva_clave()})


def _crear_ok(cliente, **extra) -> dict:
    """Crea un préstamo y exige que se haya creado."""
    respuesta = _crear(cliente, **extra)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _pagar(cliente, prestamo_id, cuota, importe, clave=None, **cuentas):
    """Paga una cuota (devuelve la respuesta sin validar el estado)."""
    return cliente.post(
        f"{LOANS}/{prestamo_id}/payments",
        json={"cuota_numero": cuota, "importe": importe, **cuentas},
        headers={"Idempotency-Key": clave or nueva_clave()},
    )


def _saldos(cliente) -> dict[str, Decimal]:
    """Saldo actual por nombre de cuenta."""
    return {c["nombre"]: Decimal(c["saldo_actual"]) for c in cliente.get("/api/v1/accounts").json()}


@pytest.fixture
def entorno(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Hogar con Ana, Luis y Marta, un fondo común y una cuenta personal para cada uno."""
    hogar = crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    crear_integrante(admin, "Luis")
    crear_integrante(admin, "Marta")
    ids = integrantes(admin)
    comun = crear_cuenta(admin, "Fondo común", saldo=2000000, tipo="banco")
    luis = crear_cuenta(admin, "Fondo de Luis", saldo=1000000, tipo="personal", propietario_id=ids["Luis"])
    marta = crear_cuenta(admin, "Fondo de Marta", saldo=500000, tipo="personal", propietario_id=ids["Marta"])
    return {"admin": admin, "ids": ids, "comun": comun["id"], "luis": luis["id"], "marta": marta["id"], "hogar": hogar}


def test_prestamo_al_hogar_con_interes_genera_cuotas_exactas(entorno):
    """Un banco presta 1.200.000 y se devuelven 1.320.000 en 12 cuotas de 110.000; el desembolso no es ingreso."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco Ejemplo", total_a_pagar=1320000, cuenta_destino_id=entorno["comun"])
    assert p["estado"] == "activo" and p["importe"] == "1200000" and p["total_a_pagar"] == "1320000"
    assert p["saldo_pendiente"] == "1320000" and p["pagado"] == "0"
    assert len(p["cuotas"]) == 12 and {c["importe"] for c in p["cuotas"]} == {"110000"}
    assert _saldos(admin)["Fondo común"] == Decimal("3200000")
    desembolso = admin.get("/api/v1/transactions", params={"tipo": "desembolso_prestamo"}).json()
    assert desembolso["total"] == 1 and desembolso["items"][0]["id"] == p["desembolso_movimiento_id"]
    assert admin.get("/api/v1/transactions", params={"tipo": "ingreso"}).json()["total"] == 0


def test_cuotas_que_no_dividen_exacto_suman_el_total_y_respetan_fin_de_mes(entorno):
    """100.000 en 3 cuotas: 33.334 + 33.333 + 33.333; las fechas siguen el calendario (31 ene -> 28 feb)."""
    admin = entorno["admin"]
    p = _crear_ok(
        admin, tipo="al_hogar", contraparte_nombre="Tercero", importe=100000, numero_cuotas=3,
        fecha="2026-01-15", primer_vencimiento="2026-01-31", cuenta_destino_id=entorno["comun"],
    )
    assert [c["importe"] for c in p["cuotas"]] == ["33334", "33333", "33333"]
    assert sum(Decimal(c["importe"]) for c in p["cuotas"]) == Decimal(100000)
    assert [c["fecha_vencimiento"] for c in p["cuotas"]] == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_fechas_por_defecto_y_calendario():
    """sumar_meses ajusta al último día del mes cuando el día no existe."""
    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2028, 1, 31), 1) == date(2028, 2, 29)  # bisiesto
    assert sumar_meses(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert sumar_meses(date(2026, 12, 15), 1) == date(2027, 1, 15)


@pytest.mark.parametrize(
    "importe, pagado, dias, esperado",
    [(100, 0, 5, "pendiente"), (100, 40, 5, "parcialmente_pagada"), (100, 100, 5, "pagada"),
     (100, 0, -1, "vencida"), (100, 40, -1, "vencida"), (100, 100, -9, "pagada"), (100, 0, 0, "pendiente")],
)
def test_estado_de_una_cuota(importe, pagado, dias, esperado):
    """Pagada > vencida > parcial > pendiente."""
    hoy = hoy_colombia()
    assert estado_de_cuota(Decimal(importe), Decimal(pagado), hoy + timedelta(days=dias), hoy) == esperado


def test_pagar_cuotas_total_y_parcialmente_hasta_saldar_el_prestamo(entorno):
    """El pago de cuota sale del fondo común, no es gasto, y al saldar todas el préstamo queda 'pagado'."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=300000, numero_cuotas=3, cuenta_destino_id=entorno["comun"])
    antes = _saldos(admin)["Fondo común"]

    parcial = _pagar(admin, p["id"], 1, 40000, cuenta_origen_id=entorno["comun"])
    assert parcial.status_code == 201
    cuota1 = parcial.json()["prestamo"]["cuotas"][0]
    assert cuota1["estado"] == "parcialmente_pagada" and cuota1["saldo"] == "60000"
    assert _saldos(admin)["Fondo común"] == antes - 40000

    for n, monto in ((1, 60000), (2, 100000), (3, 100000)):
        assert _pagar(admin, p["id"], n, monto, cuenta_origen_id=entorno["comun"]).status_code == 201
    final = admin.get(f"{LOANS}/{p['id']}").json()
    assert final["estado"] == "pagado" and final["saldo_pendiente"] == "0" and final["pagado"] == "300000"
    assert len(final["pagos"]) == 4
    # Las cuotas no son gastos del hogar ni se reparten entre los integrantes.
    assert admin.get("/api/v1/transactions", params={"tipo": "gasto"}).json()["total"] == 0
    assert admin.get("/api/v1/transactions", params={"tipo": "pago_cuota"}).json()["total"] == 4


def test_las_cuotas_no_cuentan_como_gasto_ni_se_reparten(entorno):
    """Regla 6: aunque exista una regla de reparto, pagar una cuota no genera obligación esperada."""
    admin, ids = entorno["admin"], entorno["ids"]
    regla_ok(admin, [{"integrante_id": i, "tipo": "parte"} for i in ids.values()])
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=90000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    _pagar(admin, p["id"], 1, 90000, cuenta_origen_id=entorno["comun"])
    resumen = admin.get("/api/v1/contributions/summary").json()
    assert resumen["total_esperado"] == "0" and resumen["gastos_sin_distribuir"] == "0"


def test_pagos_invalidos_de_cuota(entorno):
    """Sobrepago, cuota inexistente, cuentas equivocadas y saldo insuficiente se rechazan sin dejar rastro."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=100000, numero_cuotas=2, cuenta_destino_id=entorno["comun"])
    assert _pagar(admin, p["id"], 1, 50001, cuenta_origen_id=entorno["comun"]).status_code == 422
    assert _pagar(admin, p["id"], 9, 1000, cuenta_origen_id=entorno["comun"]).status_code == 404
    assert _pagar(admin, p["id"], 1, 1000).status_code == 422                                   # sin cuenta
    assert _pagar(admin, p["id"], 1, 1000, cuenta_origen_id=entorno["luis"]).status_code == 422  # cuenta personal
    assert _pagar(admin, p["id"], 1, 1000, cuenta_origen_id=entorno["comun"], cuenta_destino_id=entorno["luis"]).status_code == 422
    assert admin.get(f"{LOANS}/{p['id']}").json()["pagado"] == "0"


def test_prestamo_del_hogar_a_un_tercero(entorno):
    """El hogar presta: el dinero sale del fondo común y las cuotas pagadas vuelven a entrar."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="del_hogar", contraparte_nombre="Vecino", importe=400000, numero_cuotas=2, cuenta_origen_id=entorno["comun"])
    assert _saldos(admin)["Fondo común"] == Decimal("1600000")
    assert _crear(admin, tipo="del_hogar", contraparte_nombre="Vecino", cuenta_destino_id=entorno["comun"]).status_code == 422
    assert _pagar(admin, p["id"], 1, 200000, cuenta_destino_id=entorno["comun"]).status_code == 201
    assert _saldos(admin)["Fondo común"] == Decimal("1800000")
    assert _pagar(admin, p["id"], 2, 1000, cuenta_origen_id=entorno["comun"]).status_code == 422


def test_prestamo_entre_integrantes_usa_las_cuentas_personales(entorno):
    """Luis le presta 200.000 a Marta: sale del fondo de Luis y entra al de Marta; las cuotas viajan al revés."""
    admin, ids = entorno["admin"], entorno["ids"]
    base = {"tipo": "entre_integrantes", "importe": 200000, "numero_cuotas": 2,
            "prestamista_integrante_id": ids["Luis"], "prestatario_integrante_id": ids["Marta"]}
    assert _crear(admin, **base, cuenta_origen_id=entorno["marta"], cuenta_destino_id=entorno["luis"]).status_code == 422  # al revés
    assert _crear(admin, **base, cuenta_origen_id=entorno["luis"]).status_code == 422                                      # falta destino
    assert _crear(admin, **base, cuenta_origen_id=entorno["comun"], cuenta_destino_id=entorno["marta"]).status_code == 422  # origen no personal
    p = _crear_ok(admin, **base, cuenta_origen_id=entorno["luis"], cuenta_destino_id=entorno["marta"])
    s = _saldos(admin)
    assert s["Fondo de Luis"] == Decimal(800000) and s["Fondo de Marta"] == Decimal(700000) and s["Fondo común"] == Decimal(2000000)

    assert _pagar(admin, p["id"], 1, 100000, cuenta_origen_id=entorno["luis"], cuenta_destino_id=entorno["marta"]).status_code == 422
    assert _pagar(admin, p["id"], 1, 100000, cuenta_origen_id=entorno["marta"], cuenta_destino_id=entorno["luis"]).status_code == 201
    s = _saldos(admin)
    assert s["Fondo de Luis"] == Decimal(900000) and s["Fondo de Marta"] == Decimal(600000)
    assert admin.get("/api/v1/transactions", params={"tipo": "gasto"}).json()["total"] == 0
    resumen = {f["nombre"]: f for f in admin.get("/api/v1/contributions/summary").json()["integrantes"]}
    assert resumen["Marta"]["pagos_directos"] == "0"  # una cuota entre personas no es un pago directo por el hogar


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tipo": "al_hogar"},                                                            # sin prestamista
        {"tipo": "al_hogar", "contraparte_nombre": "X", "prestamista_integrante_id": "ID_LUIS"},  # dos prestamistas
        {"tipo": "al_hogar", "contraparte_nombre": "X", "prestatario_integrante_id": "ID_LUIS"},  # prestatario en préstamo al hogar
        {"tipo": "del_hogar"},                                                           # sin prestatario
        {"tipo": "del_hogar", "contraparte_nombre": "X", "prestamista_integrante_id": "ID_LUIS"},
        {"tipo": "entre_integrantes", "prestamista_integrante_id": "ID_LUIS"},           # falta prestatario
        {"tipo": "entre_integrantes", "prestamista_integrante_id": "ID_LUIS", "prestatario_integrante_id": "ID_LUIS"},
        {"tipo": "entre_integrantes", "prestamista_integrante_id": "ID_LUIS", "prestatario_integrante_id": "ID_MARTA", "contraparte_nombre": "X"},
    ],
)
def test_partes_incoherentes_se_rechazan(entorno, cuerpo):
    """Las partes deben corresponder al tipo de préstamo."""
    ids = entorno["ids"]
    cuerpo = {k: (ids["Luis"] if v == "ID_LUIS" else ids["Marta"] if v == "ID_MARTA" else v) for k, v in cuerpo.items()}
    respuesta = _crear(entorno["admin"], **cuerpo, cuenta_destino_id=entorno["comun"])
    assert respuesta.status_code == 422


def test_validaciones_de_importes_cuotas_y_fechas(entorno):
    """Total menor al importe, cuotas fuera de rango, fechas incoherentes y centavos se rechazan."""
    admin = entorno["admin"]
    base = {"tipo": "al_hogar", "contraparte_nombre": "Banco", "cuenta_destino_id": entorno["comun"]}
    hoy = hoy_colombia()
    assert _crear(admin, **base, total_a_pagar=1000).status_code == 422
    assert _crear(admin, **base, numero_cuotas=0).status_code == 422
    assert _crear(admin, **base, numero_cuotas=361).status_code == 422
    assert _crear(admin, **base, importe="100.50").status_code == 422
    assert _crear(admin, **base, fecha=str(hoy + timedelta(days=1))).status_code == 422
    assert _crear(admin, **base, fecha=str(hoy), primer_vencimiento=str(hoy - timedelta(days=1))).status_code == 422
    assert admin.get(LOANS).json()["total"] == 0 and admin.get("/api/v1/transactions").json()["total"] == 0


def test_prestamo_repetido_con_la_misma_clave_no_se_duplica(entorno):
    """Idempotencia: reenviar la creación devuelve el mismo préstamo y un solo desembolso."""
    admin = entorno["admin"]
    clave = nueva_clave()
    datos = {"tipo": "al_hogar", "contraparte_nombre": "Banco", "cuenta_destino_id": entorno["comun"]}
    primero = _crear(admin, clave, **datos)
    repetido = _crear(admin, clave, **datos)
    assert primero.status_code == 201 and repetido.status_code == 200
    assert primero.json()["id"] == repetido.json()["id"]
    assert admin.get(LOANS).json()["total"] == 1
    assert _saldos(admin)["Fondo común"] == Decimal("3200000")
    assert _crear(admin, clave, **datos, importe=5000).status_code == 409


def test_pago_de_cuota_repetido_no_se_duplica(entorno):
    """Reenviar el mismo pago de cuota lo cobra una sola vez."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=100000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    clave = nueva_clave()
    assert _pagar(admin, p["id"], 1, 30000, clave, cuenta_origen_id=entorno["comun"]).status_code == 201
    assert _pagar(admin, p["id"], 1, 30000, clave, cuenta_origen_id=entorno["comun"]).status_code == 200
    assert admin.get(f"{LOANS}/{p['id']}").json()["pagado"] == "30000"


def test_pagos_simultaneos_no_pueden_superar_el_saldo_de_la_cuota(entorno, nuevo_cliente, iniciar_sesion):
    """Concurrencia real: cuota de 100.000 y cuatro pagos simultáneos de 60.000 => solo uno pasa."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=100000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    clientes = [iniciar_sesion(nuevo_cliente(), ADMIN) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        respuestas = list(pool.map(lambda c: _pagar(c, p["id"], 1, 60000, cuenta_origen_id=entorno["comun"]), clientes))
    assert sorted(r.status_code for r in respuestas) == [201, 422, 422, 422]
    assert admin.get(f"{LOANS}/{p['id']}").json()["pagado"] == "60000"


def test_revertir_pagos_y_desembolso(entorno):
    """Se puede revertir un pago (la cuota vuelve a deber); el desembolso solo sin pagos, y deja el préstamo anulado."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=100000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    pago = _pagar(admin, p["id"], 1, 100000, cuenta_origen_id=entorno["comun"]).json()["pago"]
    assert admin.get(f"{LOANS}/{p['id']}").json()["estado"] == "pagado"

    # Con pagos confirmados no se puede deshacer el desembolso.
    rechazo = revertir(admin, p["desembolso_movimiento_id"], "Préstamo registrado por error")
    assert rechazo.status_code == 422 and "reviértalos" in rechazo.json()["error"]["mensaje"]

    assert revertir(admin, pago["movimiento_id"], "Pago equivocado").status_code == 201
    detalle = admin.get(f"{LOANS}/{p['id']}").json()
    assert detalle["estado"] == "activo" and detalle["saldo_pendiente"] == "100000"
    assert detalle["pagos"][0]["estado_movimiento"] == "revertida"

    assert revertir(admin, p["desembolso_movimiento_id"], "Préstamo registrado por error").status_code == 201
    anulado = admin.get(f"{LOANS}/{p['id']}").json()
    assert anulado["estado"] == "anulado" and anulado["saldo_pendiente"] == "0"
    assert _pagar(admin, p["id"], 1, 1000, cuenta_origen_id=entorno["comun"]).status_code == 422
    assert _saldos(admin)["Fondo común"] == Decimal("2000000")


def test_cuota_vencida(entorno):
    """Un préstamo con primer vencimiento en el pasado marca esa cuota como vencida."""
    admin = entorno["admin"]
    hoy = hoy_colombia()
    p = _crear_ok(
        admin, tipo="al_hogar", contraparte_nombre="Banco", importe=100000, numero_cuotas=2,
        fecha=str(hoy - timedelta(days=90)), primer_vencimiento=str(hoy - timedelta(days=30)), cuenta_destino_id=entorno["comun"],
    )
    assert [c["estado"] for c in p["cuotas"]] == ["vencida", "pendiente"]


def test_listado_filtros_y_paginacion(entorno):
    """Se listan con total, se filtran por estado y se paginan."""
    admin = entorno["admin"]
    for _ in range(3):
        _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=10000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    pagado = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=10000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    _pagar(admin, pagado["id"], 1, 10000, cuenta_origen_id=entorno["comun"])
    assert admin.get(LOANS).json()["total"] == 4
    assert admin.get(LOANS, params={"estado": "activo"}).json()["total"] == 3
    assert admin.get(LOANS, params={"estado": "pagado"}).json()["total"] == 1
    assert len(admin.get(LOANS, params={"limite": 2, "desplazamiento": 2}).json()["items"]) == 2
    assert admin.get(LOANS, params={"estado": "inventado"}).status_code == 422


def test_permisos_y_aislamiento_de_prestamos(entorno, crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro consulta pero no crea ni paga; otro hogar no ve nada ni puede pagar."""
    admin = entorno["admin"]
    p = _crear_ok(admin, tipo="al_hogar", contraparte_nombre="Banco", importe=50000, numero_cuotas=1, cuenta_destino_id=entorno["comun"])
    crear_miembro(entorno["hogar"], "Pablo Miembro", "pablo@example.com")
    pablo = iniciar_sesion(nuevo_cliente(), "pablo@example.com")
    assert pablo.get(LOANS).status_code == 200 and pablo.get(f"{LOANS}/{p['id']}").status_code == 200
    assert _crear(pablo, tipo="al_hogar", contraparte_nombre="X", cuenta_destino_id=entorno["comun"]).status_code == 403
    assert _pagar(pablo, p["id"], 1, 1000, cuenta_origen_id=entorno["comun"]).status_code == 403
    assert cliente.get(LOANS).status_code == 401

    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuenta_b = crear_cuenta(admin_b, "Caja", saldo=100000)
    assert admin_b.get(LOANS).json()["total"] == 0
    assert admin_b.get(f"{LOANS}/{p['id']}").status_code == 404
    assert _pagar(admin_b, p["id"], 1, 1000, cuenta_origen_id=cuenta_b["id"]).status_code == 404
    assert _crear(admin_b, tipo="al_hogar", contraparte_nombre="X", cuenta_destino_id=entorno["comun"]).status_code == 404