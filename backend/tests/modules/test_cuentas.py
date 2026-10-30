# backend/tests/modules/test_cuentas.py
# Pruebas de cuentas: creación, reglas de propietario, saldos derivados y aislamiento.

from decimal import Decimal

from tests.ayudas import crear_cuenta, gasto, ingreso, saldos

CUENTAS = "/api/v1/accounts"
ADMIN = "ana@example.com"


def _admin(crear_hogar, nuevo_cliente, iniciar_sesion, **kwargs):
    """Hogar con administrador y su cliente autenticado."""
    crear_hogar(**kwargs)
    return iniciar_sesion(nuevo_cliente(), kwargs.get("email", ADMIN))


def test_crear_cuenta_comun_con_saldo_inicial(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Una cuenta de fondo común nace con su saldo inicial como saldo actual."""
    admin = _admin(crear_hogar, nuevo_cliente, iniciar_sesion)
    cuenta = crear_cuenta(admin, "Efectivo del hogar", saldo=500000)
    assert cuenta["es_fondo_comun"] is True
    assert cuenta["propietario_id"] is None
    assert cuenta["saldo_inicial"] == "500000" and cuenta["saldo_actual"] == "500000"
    assert isinstance(cuenta["saldo_actual"], str)  # los importes viajan como texto, nunca como float


def test_cuenta_personal_requiere_propietario_del_mismo_hogar(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Las cuentas personales exigen propietario; las comunes no pueden tenerlo."""
    admin = _admin(crear_hogar, nuevo_cliente, iniciar_sesion)
    integrante = admin.get("/api/v1/members").json()[0]

    sin_dueno = admin.post(CUENTAS, json={"nombre": "Fondo Ana", "tipo": "personal"})
    assert sin_dueno.status_code == 422
    comun_con_dueno = admin.post(
        CUENTAS, json={"nombre": "Banco", "tipo": "banco", "propietario_id": integrante["id"]}
    )
    assert comun_con_dueno.status_code == 422

    personal = crear_cuenta(admin, "Fondo Ana", tipo="personal", propietario_id=integrante["id"])
    assert personal["es_fondo_comun"] is False
    assert personal["propietario_id"] == integrante["id"]


def test_no_se_asigna_como_propietario_a_un_integrante_de_otro_hogar(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: el propietario debe pertenecer al hogar de la sesión."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    integrante_de_b = admin_b.get("/api/v1/members").json()[0]
    respuesta = admin_a.post(
        CUENTAS, json={"nombre": "Fondo robado", "tipo": "personal", "propietario_id": integrante_de_b["id"]}
    )
    assert respuesta.status_code == 404


def test_validaciones_de_la_cuenta(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Saldos con centavos o negativos, nombres repetidos y tipos desconocidos se rechazan."""
    admin = _admin(crear_hogar, nuevo_cliente, iniciar_sesion)
    crear_cuenta(admin, "Banco", tipo="banco")
    assert admin.post(CUENTAS, json={"nombre": "A", "tipo": "banco", "saldo_inicial": "100.50"}).status_code == 422
    assert admin.post(CUENTAS, json={"nombre": "B", "tipo": "banco", "saldo_inicial": -1}).status_code == 422
    assert admin.post(CUENTAS, json={"nombre": "C", "tipo": "criptomoneda"}).status_code == 422
    assert admin.post(CUENTAS, json={"nombre": "BANCO", "tipo": "banco"}).status_code == 409


def test_el_miembro_ve_las_cuentas_pero_no_las_crea(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion):
    """El rol miembro es de solo lectura también en cuentas."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    crear_cuenta(admin, "Banco", tipo="banco")
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert marta.get(CUENTAS).status_code == 200
    assert len(marta.get(CUENTAS).json()) == 1
    assert marta.post(CUENTAS, json={"nombre": "Otra", "tipo": "banco"}).status_code == 403


def test_sin_sesion_no_hay_acceso_a_cuentas(bd, cliente):
    """Los endpoints de cuentas exigen autenticación."""
    assert cliente.get(CUENTAS).status_code == 401
    assert cliente.post(CUENTAS, json={"nombre": "X", "tipo": "banco"}).status_code == 401


def test_el_saldo_se_deriva_de_los_movimientos(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Saldo actual = saldo inicial + ingresos - gastos, calculado desde el libro."""
    admin = _admin(crear_hogar, nuevo_cliente, iniciar_sesion)
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    ingreso(admin, cuenta["id"], 250000)
    gasto(admin, cuenta["id"], 80000)
    assert saldos(admin)["Efectivo"] == Decimal("270000")


def test_un_hogar_no_ve_las_cuentas_de_otro(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: cada hogar solo lista sus propias cuentas."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    crear_cuenta(admin_a, "Cuenta de A", saldo=1000)
    crear_cuenta(admin_b, "Cuenta de B", saldo=2000)
    assert [c["nombre"] for c in admin_a.get(CUENTAS).json()] == ["Cuenta de A"]
    assert [c["nombre"] for c in admin_b.get(CUENTAS).json()] == ["Cuenta de B"]