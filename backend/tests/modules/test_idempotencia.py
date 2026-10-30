# backend/tests/modules/test_idempotencia.py
# Pruebas de protección contra duplicados y de concurrencia real (varias solicitudes a la vez).

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from tests.ayudas import crear_cuenta, nueva_clave, registrar, revertir, saldos

MOVS = "/api/v1/transactions"
ADMIN = "ana@example.com"


def _preparar(crear_hogar, nuevo_cliente, iniciar_sesion, saldo=1000000):
    """Hogar con administrador y una cuenta con saldo."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    return admin, crear_cuenta(admin, "Efectivo", saldo=saldo)


def test_repetir_la_misma_solicitud_no_duplica_el_movimiento(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Misma clave y mismos datos: se devuelve el original (200) y el saldo cambia una sola vez."""
    admin, cuenta = _preparar(crear_hogar, nuevo_cliente, iniciar_sesion)
    clave = nueva_clave()
    datos = {"tipo": "gasto", "importe": 100000, "cuenta_origen_id": cuenta["id"]}
    primera = registrar(admin, clave, **datos)
    segunda = registrar(admin, clave, **datos)
    tercera = registrar(admin, clave, **datos)
    assert primera.status_code == 201
    assert segunda.status_code == tercera.status_code == 200
    assert primera.json()["id"] == segunda.json()["id"] == tercera.json()["id"]
    assert admin.get(MOVS).json()["total"] == 1
    assert saldos(admin)["Efectivo"] == Decimal("900000")


def test_la_misma_clave_con_datos_distintos_es_un_conflicto(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Reutilizar una clave para otra operación se rechaza (409) y no crea nada nuevo."""
    admin, cuenta = _preparar(crear_hogar, nuevo_cliente, iniciar_sesion)
    clave = nueva_clave()
    assert registrar(admin, clave, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"]).status_code == 201
    distinta = registrar(admin, clave, tipo="gasto", importe=2000, cuenta_origen_id=cuenta["id"])
    assert distinta.status_code == 409
    assert admin.get(MOVS).json()["total"] == 1


def test_claves_iguales_en_hogares_distintos_no_chocan(crear_hogar, nuevo_cliente, iniciar_sesion):
    """La clave es única por hogar: dos hogares pueden usar el mismo texto."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuenta_a = crear_cuenta(admin_a, "Cuenta")
    cuenta_b = crear_cuenta(admin_b, "Cuenta")
    clave = nueva_clave()
    assert registrar(admin_a, clave, tipo="ingreso", importe=5000, cuenta_destino_id=cuenta_a["id"]).status_code == 201
    assert registrar(admin_b, clave, tipo="ingreso", importe=5000, cuenta_destino_id=cuenta_b["id"]).status_code == 201


def test_dos_solicitudes_identicas_simultaneas_crean_un_solo_movimiento(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Concurrencia real: dos hilos con la misma clave a la vez producen un único movimiento."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000000)
    clientes = [iniciar_sesion(nuevo_cliente(), ADMIN) for _ in range(6)]
    clave = nueva_clave()
    datos = {"tipo": "gasto", "importe": 50000, "cuenta_origen_id": cuenta["id"]}

    with ThreadPoolExecutor(max_workers=6) as pool:
        respuestas = list(pool.map(lambda c: registrar(c, clave, **datos), clientes))

    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200] * 5 + [201]
    assert len({r.json()["id"] for r in respuestas}) == 1
    assert admin.get(MOVS).json()["total"] == 1
    assert saldos(admin)["Efectivo"] == Decimal("950000")


def test_dos_gastos_simultaneos_no_pueden_gastar_el_mismo_saldo(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Con 100.000 de saldo, dos gastos simultáneos de 60.000 (claves distintas): solo uno pasa."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    clientes = [iniciar_sesion(nuevo_cliente(), ADMIN) for _ in range(4)]
    datos = {"tipo": "gasto", "importe": 60000, "cuenta_origen_id": cuenta["id"]}

    with ThreadPoolExecutor(max_workers=4) as pool:
        respuestas = list(pool.map(lambda c: registrar(c, nueva_clave(), **datos), clientes))

    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [201, 422, 422, 422]
    assert saldos(admin)["Efectivo"] == Decimal("40000")  # nunca queda negativo


def test_la_reversion_tambien_es_idempotente(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Repetir la misma reversión devuelve la ya creada (200) sin duplicarla."""
    admin, cuenta = _preparar(crear_hogar, nuevo_cliente, iniciar_sesion)
    original = registrar(admin, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"]).json()
    clave = nueva_clave()
    primera = revertir(admin, original["id"], clave=clave)
    repetida = revertir(admin, original["id"], clave=clave)
    assert primera.status_code == 201 and repetida.status_code == 200
    assert primera.json()["id"] == repetida.json()["id"]
    assert admin.get(MOVS, params={"tipo": "reversion"}).json()["total"] == 1


def test_una_clave_usada_para_crear_no_sirve_para_revertir(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Las claves identifican una operación concreta: reutilizarlas en otra da conflicto."""
    admin, cuenta = _preparar(crear_hogar, nuevo_cliente, iniciar_sesion)
    clave = nueva_clave()
    original = registrar(admin, clave, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"]).json()
    assert revertir(admin, original["id"], clave=clave).status_code == 409
    assert saldos(admin)["Efectivo"] == Decimal("999000")