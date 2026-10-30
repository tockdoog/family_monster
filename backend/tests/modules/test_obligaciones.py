# backend/tests/modules/test_obligaciones.py
# Pruebas de obligaciones: pagos parciales, estados, anulación, concurrencia y aislamiento.

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest

from app.modules.obligations.service import calcular_estado
from app.shared.fechas import hoy_colombia
from tests.ayudas import (
    categoria_id,
    crear_cuenta,
    crear_obligacion,
    gasto,
    ingreso,
    nueva_clave,
    obligacion_ok,
    pagar_obligacion,
    revertir,
    saldos,
)

OBLS = "/api/v1/obligations"
ADMIN = "ana@example.com"


@pytest.fixture
def admin(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Administrador autenticado de un hogar."""
    crear_hogar()
    return iniciar_sesion(nuevo_cliente(), ADMIN)


@pytest.mark.parametrize(
    "importe, pagado, dias, anulada, esperado",
    [
        (250000, 0, 5, False, "pendiente"),
        (250000, 100000, 5, False, "parcialmente_pagada"),
        (250000, 250000, 5, False, "pagada"),
        (250000, 0, -1, False, "vencida"),
        (250000, 100000, -1, False, "vencida"),          # vencida pesa más que parcial
        (250000, 250000, -30, False, "pagada"),          # pagada tarde sigue siendo pagada
        (250000, 0, 5, True, "anulada"),
        (250000, 250000, -5, True, "anulada"),           # anulada pesa más que todo
        (250000, 0, 0, False, "pendiente"),              # vence hoy: todavía no está vencida
    ],
)
def test_calculo_del_estado(importe, pagado, dias, anulada, esperado):
    """Prioridad: anulada > pagada > vencida > parcialmente pagada > pendiente."""
    hoy = hoy_colombia()
    assert calcular_estado(Decimal(importe), Decimal(pagado), hoy + timedelta(days=dias), anulada, hoy) == esperado


def test_pago_parcial_deja_el_saldo_pendiente_correcto(admin):
    """Regla 4: obligación de 250.000 con un pago de 100.000 => saldo pendiente de 150.000."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000000)
    obl = obligacion_ok(admin, importe=250000)
    assert obl["estado"] == "pendiente" and obl["saldo_pendiente"] == "250000"

    respuesta = pagar_obligacion(admin, obl["id"], 100000, cuenta["id"])
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["obligacion"]["pagado"] == "100000"
    assert cuerpo["obligacion"]["saldo_pendiente"] == "150000"
    assert cuerpo["obligacion"]["estado"] == "parcialmente_pagada"
    assert saldos(admin)["Efectivo"] == Decimal("900000")

    segundo = pagar_obligacion(admin, obl["id"], 150000, cuenta["id"]).json()
    assert segundo["obligacion"]["estado"] == "pagada" and segundo["obligacion"]["saldo_pendiente"] == "0"


def test_el_pago_es_un_movimiento_real_vinculado(admin):
    """El pago crea un movimiento 'pago_obligacion' con la categoría de la obligación; no es gasto ordinario."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    obl = obligacion_ok(admin, importe=80000, categoria="Energía")
    pago = pagar_obligacion(admin, obl["id"], 80000, cuenta["id"]).json()["pago"]
    movs = admin.get("/api/v1/transactions", params={"tipo": "pago_obligacion"}).json()
    assert movs["total"] == 1
    assert movs["items"][0]["id"] == pago["movimiento_id"]
    assert movs["items"][0]["categoria_id"] == categoria_id(admin, "Energía")
    assert admin.get("/api/v1/transactions", params={"tipo": "gasto"}).json()["total"] == 0
    detalle = admin.get(f"{OBLS}/{obl['id']}").json()
    assert [p["movimiento_id"] for p in detalle["pagos"]] == [pago["movimiento_id"]]


def test_no_se_puede_pagar_mas_que_el_saldo(admin):
    """Un pago que supera lo pendiente se rechaza y no mueve dinero."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000000)
    obl = obligacion_ok(admin, importe=100000)
    pagar_obligacion(admin, obl["id"], 60000, cuenta["id"])
    rechazo = pagar_obligacion(admin, obl["id"], 40001, cuenta["id"])
    assert rechazo.status_code == 422 and "supera el saldo" in rechazo.json()["error"]["mensaje"]
    assert saldos(admin)["Efectivo"] == Decimal("940000")


def test_saldo_insuficiente_en_la_cuenta_no_deja_pago_registrado(admin):
    """Si la cuenta no tiene fondos, la obligación sigue intacta."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=10000)
    obl = obligacion_ok(admin, importe=50000)
    assert pagar_obligacion(admin, obl["id"], 50000, cuenta["id"]).status_code == 422
    detalle = admin.get(f"{OBLS}/{obl['id']}").json()
    assert detalle["pagado"] == "0" and detalle["pagos"] == []


def test_pago_repetido_con_la_misma_clave_no_se_duplica(admin):
    """Idempotencia: reenviar el pago devuelve el original (200) y se cobra una sola vez."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    obl = obligacion_ok(admin, importe=200000)
    clave = nueva_clave()
    primero = pagar_obligacion(admin, obl["id"], 50000, cuenta["id"], clave)
    repetido = pagar_obligacion(admin, obl["id"], 50000, cuenta["id"], clave)
    assert primero.status_code == 201 and repetido.status_code == 200
    assert primero.json()["pago"]["movimiento_id"] == repetido.json()["pago"]["movimiento_id"]
    assert saldos(admin)["Efectivo"] == Decimal("450000")
    assert pagar_obligacion(admin, obl["id"], 60000, cuenta["id"], clave).status_code == 409


def test_dos_pagos_simultaneos_no_pueden_superar_el_saldo(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Concurrencia real: con 250.000 pendientes, dos pagos simultáneos de 150.000 => solo uno pasa."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000000)
    obl = obligacion_ok(admin, importe=250000)
    clientes = [iniciar_sesion(nuevo_cliente(), ADMIN) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        respuestas = list(pool.map(lambda c: pagar_obligacion(c, obl["id"], 150000, cuenta["id"]), clientes))
    assert sorted(r.status_code for r in respuestas) == [201, 422, 422, 422]
    assert admin.get(f"{OBLS}/{obl['id']}").json()["pagado"] == "150000"
    assert saldos(admin)["Efectivo"] == Decimal("850000")


def test_revertir_un_pago_restaura_el_saldo_pendiente(admin):
    """Al revertir el movimiento del pago, la obligación vuelve a deber ese dinero (se deriva del libro)."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    obl = obligacion_ok(admin, importe=200000)
    pago = pagar_obligacion(admin, obl["id"], 200000, cuenta["id"]).json()["pago"]
    assert admin.get(f"{OBLS}/{obl['id']}").json()["estado"] == "pagada"

    assert revertir(admin, pago["movimiento_id"], "Pago equivocado").status_code == 201
    detalle = admin.get(f"{OBLS}/{obl['id']}").json()
    assert detalle["estado"] == "pendiente" and detalle["saldo_pendiente"] == "200000"
    assert detalle["pagos"][0]["estado_movimiento"] == "revertida"  # el historial se conserva
    assert saldos(admin)["Efectivo"] == Decimal("500000")
    assert pagar_obligacion(admin, obl["id"], 200000, cuenta["id"]).status_code == 201


def test_obligacion_vencida(admin):
    """Una obligación con vencimiento pasado y saldo se marca vencida y se puede filtrar."""
    hoy = hoy_colombia()
    obl = obligacion_ok(admin, importe=90000, vence=hoy - timedelta(days=1), fecha_creacion=str(hoy - timedelta(days=20)))
    assert obl["estado"] == "vencida"
    obligacion_ok(admin, importe=10000)
    assert admin.get(OBLS, params={"estado": "vencida"}).json()["total"] == 1
    assert admin.get(OBLS, params={"estado": "pendiente"}).json()["total"] == 1
    assert admin.get(OBLS, params={"estado": "inventado"}).status_code == 422


def test_anular_una_obligacion(admin):
    """Se anula con motivo, ya no admite pagos y no se puede anular dos veces ni con pagos."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=500000)
    con_pagos = obligacion_ok(admin, importe=100000)
    pagar_obligacion(admin, con_pagos["id"], 10000, cuenta["id"])
    assert admin.post(f"{OBLS}/{con_pagos['id']}/cancel", json={"motivo": "Ya no aplica"}).status_code == 422

    libre = obligacion_ok(admin, importe=100000)
    assert admin.post(f"{OBLS}/{libre['id']}/cancel", json={"motivo": "ab"}).status_code == 422
    anulada = admin.post(f"{OBLS}/{libre['id']}/cancel", json={"motivo": "Factura duplicada"})
    assert anulada.status_code == 200
    assert anulada.json()["estado"] == "anulada" and anulada.json()["saldo_pendiente"] == "0"
    assert admin.post(f"{OBLS}/{libre['id']}/cancel", json={"motivo": "Factura duplicada"}).status_code == 409
    assert pagar_obligacion(admin, libre["id"], 1000, cuenta["id"]).status_code == 422


def test_validaciones_al_crear(admin, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Importes, fechas, categoría y responsable inválidos se rechazan."""
    hoy = hoy_colombia()
    assert crear_obligacion(admin, importe=0).status_code == 422
    assert crear_obligacion(admin, importe="100.50").status_code == 422
    assert crear_obligacion(admin, vence=hoy - timedelta(days=1)).status_code == 422  # vence antes de crearse
    assert crear_obligacion(admin, fecha_creacion=str(hoy + timedelta(days=1)), vence=hoy + timedelta(days=5)).status_code == 422
    assert crear_obligacion(admin, categoria_id=str(uuid.uuid4())).status_code in (404, 422)
    assert crear_obligacion(admin, responsable_id=str(uuid.uuid4())).status_code == 404

    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    categoria_ajena = categoria_id(admin_b, "Agua")
    cuerpo = {
        "descripcion": "x", "categoria_id": categoria_ajena, "importe_original": 1000,
        "fecha_vencimiento": str(hoy + timedelta(days=3)), "acreedor": "Y",
    }
    assert admin.post(OBLS, json=cuerpo).status_code == 404
    responsable_ajeno = admin_b.get("/api/v1/members").json()[0]["id"]
    assert crear_obligacion(admin, responsable_id=responsable_ajeno).status_code == 404


def test_aislamiento_entre_hogares(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Un hogar no ve, paga ni anula las obligaciones de otro."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuenta_b = crear_cuenta(admin_b, "Efectivo", saldo=500000)
    obl_a = obligacion_ok(admin_a, importe=100000)
    assert admin_b.get(OBLS).json()["total"] == 0
    assert admin_b.get(f"{OBLS}/{obl_a['id']}").status_code == 404
    assert pagar_obligacion(admin_b, obl_a["id"], 1000, cuenta_b["id"]).status_code == 404
    assert admin_b.post(f"{OBLS}/{obl_a['id']}/cancel", json={"motivo": "Intento ajeno"}).status_code == 404
    assert admin_a.get(f"{OBLS}/{obl_a['id']}").json()["estado"] == "pendiente"


def test_permisos_de_obligaciones(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro consulta pero no crea, paga ni anula; sin sesión no hay acceso."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    obl = obligacion_ok(admin, importe=50000)
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert marta.get(OBLS).status_code == 200 and marta.get(f"{OBLS}/{obl['id']}").status_code == 200
    assert crear_obligacion(marta).status_code == 403
    assert pagar_obligacion(marta, obl["id"], 1000, cuenta["id"]).status_code == 403
    assert marta.post(f"{OBLS}/{obl['id']}/cancel", json={"motivo": "Intento sin permiso"}).status_code == 403
    assert cliente.get(OBLS).status_code == 401


def test_listado_paginado_y_orden_por_vencimiento(admin):
    """Las obligaciones salen ordenadas por vencimiento y se paginan con total."""
    hoy = hoy_colombia()
    for dias in (30, 5, 20, 10):
        obligacion_ok(admin, importe=1000 * dias, vence=hoy + timedelta(days=dias))
    pagina = admin.get(OBLS, params={"limite": 3}).json()
    assert pagina["total"] == 4 and len(pagina["items"]) == 3
    assert [o["fecha_vencimiento"] for o in pagina["items"]] == [str(hoy + timedelta(days=d)) for d in (5, 10, 20)]
    assert len(admin.get(OBLS, params={"limite": 3, "desplazamiento": 3}).json()["items"]) == 1