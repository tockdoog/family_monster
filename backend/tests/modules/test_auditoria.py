# backend/tests/modules/test_auditoria.py
# Pruebas de la bitácora: qué se registra, quién la ve y que no se filtren datos sensibles.

import pytest

from tests.ayudas import crear_cuenta, gasto, ingreso, registrar, revertir

AUDIT = "/api/v1/audit"
ADMIN = "ana@example.com"


@pytest.fixture
def admin(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Administrador autenticado de un hogar."""
    crear_hogar()
    return iniciar_sesion(nuevo_cliente(), ADMIN)


def _acciones(cliente) -> list[str]:
    """Acciones registradas, de la más antigua a la más reciente."""
    return [r["accion"] for r in reversed(cliente.get(AUDIT).json()["items"])]


def test_las_operaciones_importantes_quedan_registradas(admin):
    """Hogar, integrante, cuenta, movimiento y reversión aparecen con su responsable."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    mov = gasto(admin, cuenta["id"], 5000)
    revertir(admin, mov["id"], "Cobro duplicado")
    admin.post("/api/v1/members", json={"nombre": "Luis"})

    assert _acciones(admin) == [
        "hogar_creado",
        "cuenta_creada",
        "movimiento_registrado",
        "movimiento_revertido",
        "integrante_creado",
    ]
    reversion = next(r for r in admin.get(AUDIT).json()["items"] if r["accion"] == "movimiento_revertido")
    assert reversion["motivo"] == "Cobro duplicado"
    assert reversion["entidad_id"] == mov["id"]
    assert reversion["usuario_id"] == admin.get("/api/v1/auth/me").json()["usuario"]["id"]


def test_otorgar_acceso_se_audita_sin_exponer_contrasenas(admin):
    """Se registra el rol otorgado, nunca la contraseña ni su hash."""
    luis = admin.post("/api/v1/members", json={"nombre": "Luis"}).json()
    admin.post(
        f"/api/v1/members/{luis['id']}/acceso",
        json={"email": "luis@example.com", "contrasena": "ClaveSegura2026", "rol": "miembro"},
    )
    texto = admin.get(AUDIT).text.lower()
    assert "acceso_otorgado" in texto
    for secreto in ("claveSegura2026".lower(), "argon2", "password", "contrasena"):
        assert secreto not in texto


def test_una_operacion_rechazada_no_deja_registro(admin):
    """Si el movimiento falla (saldo insuficiente) tampoco queda auditoría de un movimiento inexistente."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=1000)
    assert registrar(admin, tipo="gasto", importe=5000, cuenta_origen_id=cuenta["id"]).status_code == 422
    assert "movimiento_registrado" not in _acciones(admin)


def test_una_repeticion_idempotente_no_duplica_la_auditoria(admin):
    """Reenviar la misma solicitud no genera un segundo registro de auditoría."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    clave = "clave-repetida-0001"
    for _ in range(3):
        registrar(admin, clave, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"])
    assert _acciones(admin).count("movimiento_registrado") == 1


def test_solo_el_administrador_ve_la_bitacora(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro recibe 403 y sin sesión 401."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert marta.get(AUDIT).status_code == 403
    assert cliente.get(AUDIT).status_code == 401


def test_cada_hogar_ve_solo_su_bitacora_y_se_pagina(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento y paginación de la bitácora."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuenta = crear_cuenta(admin_a, "Cuenta A")
    for _ in range(4):
        ingreso(admin_a, cuenta["id"], 1000)
    assert admin_a.get(AUDIT).json()["total"] == 6  # hogar + cuenta + 4 movimientos
    assert admin_b.get(AUDIT).json()["total"] == 1  # solo la creación de su hogar
    pagina = admin_a.get(AUDIT, params={"limite": 2, "desplazamiento": 2}).json()
    assert len(pagina["items"]) == 2 and pagina["total"] == 6