# backend/tests/modules/test_aportes.py
# Pruebas de reglas de reparto, aportes, pagos directos, reembolsos y resumen esperado vs real.

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest

from app.shared.fechas import hoy_colombia
from tests.ayudas import (
    crear_cuenta,
    crear_integrante,
    crear_regla,
    gasto,
    integrantes,
    nueva_clave,
    obligacion_ok,
    pagar_obligacion,
    regla_ok,
    reparto,
    revertir,
)

APORTES = "/api/v1/contributions"
ADMIN = "ana@example.com"


def _item(integrante: str, tipo: str, valor=None) -> dict:
    """Ítem de una regla."""
    return {"integrante_id": integrante, "tipo": tipo, **({} if valor is None else {"valor": valor})}


@pytest.fixture
def hogar3(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Hogar con tres integrantes (Ana, Luis, Marta), una cuenta común y un cliente administrador."""
    hogar = crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    crear_integrante(admin, "Luis")
    crear_integrante(admin, "Marta")
    ids = integrantes(admin)
    comun = crear_cuenta(admin, "Fondo común", saldo=5000000, tipo="banco")
    return {"admin": admin, "ids": ids, "comun": comun, "hogar": hogar}


def _resumen(admin, **params) -> dict[str, dict]:
    """Resumen de aportes indexado por nombre."""
    cuerpo = admin.get(f"{APORTES}/summary", params=params).json()
    return {f["nombre"]: f for f in cuerpo["integrantes"]}


def _partes_iguales(ids: dict) -> list[dict]:
    """Regla de partes iguales para los tres integrantes."""
    return [_item(i, "parte") for i in ids.values()]


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------
def test_regla_de_partes_iguales_reparte_un_gasto_sin_perder_pesos(hogar3):
    """100.000 entre 3 en partes iguales: las partes suman exactamente 100.000."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    mov = gasto(admin, comun["id"], 100000)
    partes = reparto(admin, mov["id"])
    assert sum(partes.values()) == Decimal(100000)
    assert sorted(partes.values()) == [Decimal(33333), Decimal(33333), Decimal(33334)]


def test_regla_por_porcentajes(hogar3):
    """50 % / 30 % / 20 %."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, [_item(ids["Ana Admin"], "porcentaje", 50), _item(ids["Luis"], "porcentaje", 30), _item(ids["Marta"], "porcentaje", 20)])
    partes = reparto(admin, gasto(admin, comun["id"], 1000000)["id"])
    assert partes == {ids["Ana Admin"]: Decimal(500000), ids["Luis"]: Decimal(300000), ids["Marta"]: Decimal(200000)}


def test_regla_con_importe_fijo_y_resto_en_partes_iguales(hogar3):
    """Luis paga 30.000 fijos; Ana y Marta se reparten el resto por igual."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, [_item(ids["Luis"], "fijo", 30000), _item(ids["Ana Admin"], "parte"), _item(ids["Marta"], "parte")])
    partes = reparto(admin, gasto(admin, comun["id"], 100000)["id"])
    assert partes == {ids["Luis"]: Decimal(30000), ids["Ana Admin"]: Decimal(35000), ids["Marta"]: Decimal(35000)}


def test_la_regla_de_una_categoria_prevalece_sobre_la_general(hogar3):
    """Los gastos de 'Internet' usan su regla específica; los demás, la general."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids), nombre="General")
    regla_ok(admin, [_item(ids["Ana Admin"], "porcentaje", 100)], categoria="Internet", nombre="Internet de Ana")
    internet = gasto(admin, comun["id"], 90000, categoria_id=_cat(admin, "Internet"))
    mercado = gasto(admin, comun["id"], 90000, categoria_id=_cat(admin, "Mercado"))
    assert reparto(admin, internet["id"]) == {ids["Ana Admin"]: Decimal(90000)}
    assert sorted(reparto(admin, mercado["id"]).values()) == [Decimal(30000)] * 3


def _cat(admin, nombre: str) -> str:
    """Id de categoría por nombre."""
    from tests.ayudas import categoria_id

    return categoria_id(admin, nombre)


@pytest.mark.parametrize(
    "construir",
    [
        lambda i: [_item(i["Ana Admin"], "porcentaje", 60), _item(i["Luis"], "porcentaje", 30)],            # no suma 100
        lambda i: [_item(i["Ana Admin"], "parte"), _item(i["Ana Admin"], "parte")],                          # repetido
        lambda i: [_item(i["Ana Admin"], "porcentaje", 50), _item(i["Luis"], "parte")],                      # mezcla
        lambda i: [_item(i["Ana Admin"], "fijo", 1000)],                                                     # nadie cubre el resto
        lambda i: [_item(i["Ana Admin"], "porcentaje", 0), _item(i["Luis"], "porcentaje", 100)],             # porcentaje en cero
        lambda i: [_item(i["Ana Admin"], "porcentaje", 101)],                                                # sobre 100
        lambda i: [_item(i["Ana Admin"], "fijo", "1000.50"), _item(i["Luis"], "parte")],                     # centavos
        lambda i: [_item(i["Ana Admin"], "parte", 2), _item(i["Luis"], "parte")],                            # parte con valor
        lambda i: [_item(i["Ana Admin"], "otro", 1)],                                                        # tipo inventado
        lambda i: [],                                                                                        # vacía
    ],
)
def test_reglas_incoherentes_se_rechazan(hogar3, construir):
    """Porcentajes que no suman 100, repetidos, mezclas y valores inválidos no se aceptan."""
    assert crear_regla(hogar3["admin"], construir(hogar3["ids"])).status_code == 422


def test_regla_con_integrante_o_categoria_de_otro_hogar(hogar3, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: no se puede armar una regla con datos de otro hogar."""
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    ajeno = integrantes(admin_b)["Beto Admin"]
    assert crear_regla(hogar3["admin"], [_item(ajeno, "parte")]).status_code == 404
    cuerpo = {"nombre": "X", "vigente_desde": str(hoy_colombia()), "categoria_id": str(uuid.uuid4()), "items": [_item(hogar3["ids"]["Luis"], "parte")]}
    assert hogar3["admin"].post("/api/v1/contribution-rules", json=cuerpo).status_code == 404


# ---------------------------------------------------------------------------
# Vigencia: las reglas nuevas no alteran el pasado
# ---------------------------------------------------------------------------
def test_una_regla_nueva_no_modifica_los_repartos_historicos(hogar3):
    """Regla 18: al cambiar los porcentajes, los gastos ya repartidos conservan su foto original."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    hoy = hoy_colombia()
    v1 = regla_ok(admin, [_item(ids["Ana Admin"], "porcentaje", 50), _item(ids["Luis"], "porcentaje", 50)], desde=hoy - timedelta(days=30), nombre="v1")
    viejo = gasto(admin, comun["id"], 200000, fecha=str(hoy - timedelta(days=5)))
    antes = reparto(admin, viejo["id"])
    resumen_antes = _resumen(admin, desde=str(hoy - timedelta(days=10)), hasta=str(hoy))["Ana Admin"]["obligacion_esperada"]

    v2 = regla_ok(admin, [_item(ids["Ana Admin"], "porcentaje", 80), _item(ids["Luis"], "porcentaje", 20)], desde=hoy - timedelta(days=2), nombre="v2")
    # La regla anterior se cierra el día antes de que empiece la nueva.
    reglas = {r["id"]: r for r in admin.get("/api/v1/contribution-rules").json()}
    assert reglas[v1["id"]]["vigente_hasta"] == str(hoy - timedelta(days=3))
    assert reglas[v2["id"]]["vigente_hasta"] is None

    assert reparto(admin, viejo["id"]) == antes == {ids["Ana Admin"]: Decimal(100000), ids["Luis"]: Decimal(100000)}
    assert _resumen(admin, desde=str(hoy - timedelta(days=10)), hasta=str(hoy))["Ana Admin"]["obligacion_esperada"] == resumen_antes

    nuevo = gasto(admin, comun["id"], 200000)
    assert reparto(admin, nuevo["id"]) == {ids["Ana Admin"]: Decimal(160000), ids["Luis"]: Decimal(40000)}
    # Un gasto con fecha de la época de v1 registrado DESPUÉS sigue repartiéndose con v1 (la vigencia es por fecha).
    tardio = gasto(admin, comun["id"], 100000, fecha=str(hoy - timedelta(days=10)))
    assert reparto(admin, tardio["id"]) == {ids["Ana Admin"]: Decimal(50000), ids["Luis"]: Decimal(50000)}


def test_una_regla_nueva_no_puede_empezar_antes_que_la_vigente(hogar3):
    """Solo se avanza en el tiempo: una regla desde una fecha igual o anterior se rechaza."""
    admin, ids = hogar3["admin"], hogar3["ids"]
    hoy = hoy_colombia()
    regla_ok(admin, _partes_iguales(ids), desde=hoy - timedelta(days=10))
    assert crear_regla(admin, _partes_iguales(ids), desde=hoy - timedelta(days=10)).status_code == 422
    assert crear_regla(admin, _partes_iguales(ids), desde=hoy - timedelta(days=20)).status_code == 422
    assert crear_regla(admin, _partes_iguales(ids), desde=hoy - timedelta(days=1)).status_code == 201


def test_un_gasto_sin_regla_queda_sin_repartir_y_el_resumen_lo_informa(hogar3):
    """Sin regla aplicable no se inventa un reparto: se avisa cuánto quedó sin distribuir."""
    admin, comun = hogar3["admin"], hogar3["comun"]
    mov = gasto(admin, comun["id"], 70000)
    assert reparto(admin, mov["id"]) == {}
    cuerpo = admin.get(f"{APORTES}/summary").json()
    assert cuerpo["gastos_sin_distribuir"] == "70000" and cuerpo["total_esperado"] == "0"


def test_revertir_un_gasto_anula_su_reparto_en_lo_esperado(hogar3):
    """Los repartos solo cuentan mientras el gasto siga confirmado."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    mov = gasto(admin, comun["id"], 90000)
    assert admin.get(f"{APORTES}/summary").json()["total_esperado"] == "90000"
    revertir(admin, mov["id"], "Gasto registrado por error")
    assert admin.get(f"{APORTES}/summary").json()["total_esperado"] == "0"
    assert len(reparto(admin, mov["id"])) == 3  # la foto histórica se conserva


# ---------------------------------------------------------------------------
# Aportes
# ---------------------------------------------------------------------------
def _aporte(admin, integrante, importe, destino, origen=None, clave=None, **extra):
    """Registra un aporte (devuelve la respuesta sin validar el estado)."""
    cuerpo = {"integrante_id": integrante, "importe": importe, "cuenta_destino_id": destino, **extra}
    if origen:
        cuerpo["cuenta_origen_id"] = origen
    return admin.post(APORTES, json=cuerpo, headers={"Idempotency-Key": clave or nueva_clave()})


def test_un_aporte_entra_al_fondo_comun_sin_ser_ingreso(hogar3):
    """Un aporte sube el fondo común, es un movimiento 'aporte' y no cuenta como ingreso (regla 2)."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    respuesta = _aporte(admin, ids["Luis"], 400000, comun["id"])
    assert respuesta.status_code == 201 and respuesta.json()["tipo"] == "aporte"
    saldo = next(c for c in admin.get("/api/v1/accounts").json() if c["nombre"] == "Fondo común")["saldo_actual"]
    assert saldo == "5400000"
    assert admin.get("/api/v1/transactions", params={"tipo": "ingreso"}).json()["total"] == 0
    assert _resumen(admin)["Luis"]["aportes"] == "400000"


def test_aporte_desde_la_cuenta_personal(hogar3):
    """Si el dinero sale de la cuenta personal del integrante, esa cuenta baja y el fondo sube."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    personal = crear_cuenta(admin, "Fondo de Luis", saldo=300000, tipo="personal", propietario_id=ids["Luis"])
    assert _aporte(admin, ids["Luis"], 100000, comun["id"], personal["id"]).status_code == 201
    saldos = {c["nombre"]: c["saldo_actual"] for c in admin.get("/api/v1/accounts").json()}
    assert saldos["Fondo de Luis"] == "200000" and saldos["Fondo común"] == "5100000"


def test_aportes_invalidos(hogar3):
    """No se aporta a una cuenta personal, ni desde la cuenta personal de otro integrante."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    de_marta = crear_cuenta(admin, "Fondo de Marta", saldo=100000, tipo="personal", propietario_id=ids["Marta"])
    de_luis = crear_cuenta(admin, "Fondo de Luis", saldo=100000, tipo="personal", propietario_id=ids["Luis"])
    assert _aporte(admin, ids["Luis"], 1000, de_marta["id"]).status_code == 422
    assert _aporte(admin, ids["Luis"], 1000, comun["id"], de_marta["id"]).status_code == 422
    assert _aporte(admin, ids["Luis"], 1000, comun["id"], comun["id"]).status_code == 422
    assert _aporte(admin, str(uuid.uuid4()), 1000, comun["id"]).status_code == 404
    assert _aporte(admin, ids["Luis"], 0, comun["id"]).status_code == 422
    assert _aporte(admin, ids["Luis"], 500000, comun["id"], de_luis["id"]).status_code == 422  # sin saldo


def test_aporte_repetido_no_se_duplica(hogar3):
    """Idempotencia también en los aportes."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    clave = nueva_clave()
    assert _aporte(admin, ids["Luis"], 1000, comun["id"], clave=clave).status_code == 201
    assert _aporte(admin, ids["Luis"], 1000, comun["id"], clave=clave).status_code == 200
    assert _resumen(admin)["Luis"]["aportes"] == "1000"


# ---------------------------------------------------------------------------
# Resumen esperado vs real, pagos directos y reembolsos
# ---------------------------------------------------------------------------
def test_resumen_esperado_contra_real(hogar3):
    """Cada integrante ve lo que debía aportar, lo que puso, su saldo y su estado."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    gasto(admin, comun["id"], 300000)  # cada uno debe 100.000
    _aporte(admin, ids["Luis"], 150000, comun["id"])   # aporta de más
    _aporte(admin, ids["Marta"], 60000, comun["id"])   # aporta de menos
    r = _resumen(admin)
    assert r["Luis"]["obligacion_esperada"] == "100000" and r["Luis"]["saldo"] == "50000" and r["Luis"]["estado"] == "al_dia"
    assert r["Marta"]["saldo"] == "-40000" and r["Marta"]["estado"] == "pendiente"
    assert r["Ana Admin"]["aportado_neto"] == "0" and r["Ana Admin"]["saldo"] == "-100000"


def test_el_periodo_del_resumen_filtra_por_fecha(hogar3):
    """Los gastos de otro mes no cuentan en el período consultado."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    hoy = hoy_colombia()
    regla_ok(admin, _partes_iguales(ids))
    gasto(admin, comun["id"], 90000, fecha=str(hoy - timedelta(days=100)))
    gasto(admin, comun["id"], 30000)
    r = admin.get(f"{APORTES}/summary", params={"desde": str(hoy - timedelta(days=5)), "hasta": str(hoy)}).json()
    assert r["total_esperado"] == "30000"
    assert admin.get(f"{APORTES}/summary", params={"desde": str(hoy), "hasta": str(hoy - timedelta(days=1))}).status_code == 422


def test_pago_directo_con_cuenta_personal_y_reembolso(hogar3):
    """Regla 3: Luis paga con su dinero; cuenta como aporte suyo, el hogar le debe, y el reembolso lo salda."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    personal = crear_cuenta(admin, "Fondo de Luis", saldo=200000, tipo="personal", propietario_id=ids["Luis"])
    pago = gasto(admin, personal["id"], 90000)  # un solo gasto del hogar, sin duplicados

    r = _resumen(admin)["Luis"]
    assert r["pagos_directos"] == "90000" and r["aportado_neto"] == "90000"
    assert r["obligacion_esperada"] == "30000" and r["saldo"] == "60000"
    assert r["reembolso_pendiente"] == "90000"
    assert len(admin.get("/api/v1/transactions", params={"tipo": "gasto"}).json()["items"]) == 1
    assert reparto(admin, pago["id"]) and sum(reparto(admin, pago["id"]).values()) == Decimal(90000)

    def reembolsar(importe, clave=None):
        return admin.post(
            f"{APORTES}/reimbursements",
            json={"integrante_id": ids["Luis"], "importe": importe, "cuenta_origen_id": comun["id"], "cuenta_destino_id": personal["id"]},
            headers={"Idempotency-Key": clave or nueva_clave()},
        )

    assert reembolsar(90001).status_code == 422  # más de lo que se le debe
    ok = reembolsar(50000)
    assert ok.status_code == 201 and ok.json()["tipo"] == "reembolso"
    saldos = {c["nombre"]: c["saldo_actual"] for c in admin.get("/api/v1/accounts").json()}
    assert saldos["Fondo de Luis"] == "160000" and saldos["Fondo común"] == "4950000"
    r = _resumen(admin)["Luis"]
    assert r["reembolsos"] == "50000" and r["reembolso_pendiente"] == "40000" and r["aportado_neto"] == "40000"
    assert reembolsar(40000).status_code == 201
    assert _resumen(admin)["Luis"]["reembolso_pendiente"] == "0"
    assert reembolsar(1).status_code == 422
    # Los reembolsos no son gastos ni ingresos del hogar.
    assert admin.get("/api/v1/transactions", params={"tipo": "ingreso"}).json()["total"] == 0
    assert admin.get("/api/v1/transactions", params={"tipo": "gasto"}).json()["total"] == 1


def test_pagar_una_obligacion_con_cuenta_personal_es_pago_directo(hogar3):
    """Una factura pagada desde la cuenta personal cuenta como aporte directo de quien pagó."""
    admin, ids = hogar3["admin"], hogar3["ids"]
    regla_ok(admin, _partes_iguales(ids))
    personal = crear_cuenta(admin, "Fondo de Marta", saldo=300000, tipo="personal", propietario_id=ids["Marta"])
    obl = obligacion_ok(admin, importe=120000, categoria="Energía")
    pago = pagar_obligacion(admin, obl["id"], 120000, personal["id"]).json()["pago"]
    r = _resumen(admin)
    assert r["Marta"]["pagos_directos"] == "120000" and r["Marta"]["reembolso_pendiente"] == "120000"
    assert sum(reparto(admin, pago["movimiento_id"]).values()) == Decimal(120000)
    assert r["Luis"]["obligacion_esperada"] == "40000"


def test_un_reembolso_debe_ir_de_fondo_comun_a_cuenta_personal_del_integrante(hogar3):
    """Cuentas incorrectas o integrante sin deuda se rechazan."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    de_luis = crear_cuenta(admin, "Fondo de Luis", saldo=100000, tipo="personal", propietario_id=ids["Luis"])
    de_marta = crear_cuenta(admin, "Fondo de Marta", saldo=100000, tipo="personal", propietario_id=ids["Marta"])

    def reembolsar(integrante, origen, destino, importe=1000):
        return admin.post(
            f"{APORTES}/reimbursements",
            json={"integrante_id": integrante, "importe": importe, "cuenta_origen_id": origen, "cuenta_destino_id": destino},
            headers={"Idempotency-Key": nueva_clave()},
        )

    assert reembolsar(ids["Luis"], comun["id"], de_luis["id"]).status_code == 422   # no se le debe nada
    gasto(admin, de_luis["id"], 50000)
    assert reembolsar(ids["Luis"], comun["id"], de_marta["id"]).status_code == 422  # cuenta de otra persona
    assert reembolsar(ids["Luis"], de_marta["id"], de_luis["id"]).status_code == 422  # origen personal
    assert reembolsar(ids["Luis"], comun["id"], comun["id"]).status_code == 422     # destino no personal
    assert reembolsar(ids["Luis"], comun["id"], de_luis["id"]).status_code == 201


def test_dos_reembolsos_simultaneos_no_pueden_superar_lo_que_se_debe(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Concurrencia real: con 100.000 por reembolsar, cuatro reembolsos de 60.000 a la vez => solo uno pasa."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    ana = integrantes(admin)["Ana Admin"]
    comun = crear_cuenta(admin, "Fondo común", saldo=1000000, tipo="banco")
    personal = crear_cuenta(admin, "Fondo de Ana", saldo=200000, tipo="personal", propietario_id=ana)
    gasto(admin, personal["id"], 100000)
    clientes = [iniciar_sesion(nuevo_cliente(), ADMIN) for _ in range(4)]

    def reembolsar(cliente):
        return cliente.post(
            f"{APORTES}/reimbursements",
            json={"integrante_id": ana, "importe": 60000, "cuenta_origen_id": comun["id"], "cuenta_destino_id": personal["id"]},
            headers={"Idempotency-Key": nueva_clave()},
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        respuestas = list(pool.map(reembolsar, clientes))
    assert sorted(r.status_code for r in respuestas) == [201, 422, 422, 422]
    assert _resumen(admin)["Ana Admin"]["reembolso_pendiente"] == "40000"


def test_el_miembro_consulta_pero_no_modifica_aportes(hogar3, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """Con rol miembro: ve reglas y resumen (200) pero no crea reglas, aportes ni reembolsos (403)."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    crear_miembro(hogar3["hogar"], "Pablo Miembro", "pablo@example.com")
    pablo = iniciar_sesion(nuevo_cliente(), "pablo@example.com")
    cabecera = {"Idempotency-Key": nueva_clave()}
    assert pablo.get("/api/v1/contribution-rules").status_code == 200
    assert pablo.get(f"{APORTES}/summary").status_code == 200
    assert crear_regla(pablo, _partes_iguales(ids), desde=hoy_colombia()).status_code == 403
    aporte = {"integrante_id": ids["Luis"], "importe": 1000, "cuenta_destino_id": comun["id"]}
    assert pablo.post(APORTES, json=aporte, headers=cabecera).status_code == 403
    reembolso = {**aporte, "cuenta_origen_id": comun["id"], "cuenta_destino_id": comun["id"]}
    assert pablo.post(f"{APORTES}/reimbursements", json=reembolso, headers=cabecera).status_code == 403
    assert cliente.get(f"{APORTES}/summary").status_code == 401
    assert cliente.post("/api/v1/contribution-rules", json={}).status_code == 401


def test_aislamiento_de_aportes_entre_hogares(hogar3, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Otro hogar no ve las reglas, repartos ni integrantes del primero, ni puede usar sus cuentas."""
    admin, ids, comun = hogar3["admin"], hogar3["ids"], hogar3["comun"]
    regla_ok(admin, _partes_iguales(ids))
    mov = gasto(admin, comun["id"], 30000)

    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    assert admin_b.get("/api/v1/contribution-rules").json() == []
    assert admin_b.get(f"{APORTES}/distributions/{mov['id']}").status_code == 404
    assert [f["nombre"] for f in admin_b.get(f"{APORTES}/summary").json()["integrantes"]] == ["Beto Admin"]
    # No puede registrar un aporte de un integrante ni hacia una cuenta del otro hogar.
    assert _aporte(admin_b, ids["Luis"], 1000, comun["id"]).status_code == 404
    beto = integrantes(admin_b)["Beto Admin"]
    assert _aporte(admin_b, beto, 1000, comun["id"]).status_code == 404