# backend/tests/modules/test_categorias.py
# Pruebas de categorías: siembra inicial, alta, renombrado, desactivación y aislamiento.

import pytest

from tests.ayudas import categoria_id, crear_cuenta, registrar

CATS = "/api/v1/categories"
ADMIN = "ana@example.com"


@pytest.fixture
def admin(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Administrador autenticado de un hogar."""
    crear_hogar()
    return iniciar_sesion(nuevo_cliente(), ADMIN)


def test_un_hogar_nuevo_recibe_las_categorias_iniciales(admin):
    """Las 11 categorías de partida del documento existen desde el primer momento."""
    nombres = {c["nombre"] for c in admin.get(CATS).json()}
    assert nombres == {
        "Agua", "Energía", "Gas", "Internet", "Mercado", "Arriendo",
        "Reparaciones", "Transporte", "Salud", "Préstamos", "Otros",
    }


def test_crear_renombrar_y_desactivar(admin):
    """Las categorías se configuran, y nunca se borran: se desactivan."""
    creada = admin.post(CATS, json={"nombre": "  Mascotas  "})
    assert creada.status_code == 201 and creada.json()["nombre"] == "Mascotas"
    assert admin.post(CATS, json={"nombre": "mascotas"}).status_code == 409
    renombrada = admin.patch(f"{CATS}/{creada.json()['id']}", json={"nombre": "Veterinaria"})
    assert renombrada.json()["nombre"] == "Veterinaria"
    desactivada = admin.patch(f"{CATS}/{creada.json()['id']}", json={"activa": False})
    assert desactivada.json()["activa"] is False
    assert admin.patch(f"{CATS}/{creada.json()['id']}", json={}).status_code == 422
    assert admin.patch(f"{CATS}/{creada.json()['id']}", json={"nombre": "Agua"}).status_code == 409


def test_una_categoria_desactivada_no_se_puede_usar(admin):
    """Un movimiento no se puede clasificar con una categoría desactivada."""
    cuenta = crear_cuenta(admin, "Efectivo", saldo=100000)
    cat = categoria_id(admin, "Otros")
    ok = registrar(admin, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"], categoria_id=cat)
    assert ok.status_code == 201 and ok.json()["categoria_id"] == cat
    admin.patch(f"{CATS}/{cat}", json={"activa": False})
    rechazo = registrar(admin, tipo="gasto", importe=1000, cuenta_origen_id=cuenta["id"], categoria_id=cat)
    assert rechazo.status_code == 422 and "desactivada" in rechazo.json()["error"]["mensaje"]


def test_categoria_de_otro_hogar_o_en_transferencia(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Aislamiento: una categoría de otro hogar 'no existe'; y las transferencias no llevan categoría."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuenta_a = crear_cuenta(admin_a, "Efectivo", saldo=10000)
    otra_a = crear_cuenta(admin_a, "Banco", tipo="banco")
    ajena = categoria_id(admin_b, "Agua")
    assert registrar(admin_a, tipo="gasto", importe=10, cuenta_origen_id=cuenta_a["id"], categoria_id=ajena).status_code == 404
    propia = categoria_id(admin_a, "Agua")
    assert registrar(admin_a, tipo="transferencia", importe=10, cuenta_origen_id=cuenta_a["id"], cuenta_destino_id=otra_a["id"], categoria_id=propia).status_code == 422
    assert admin_b.patch(f"{CATS}/{propia}", json={"nombre": "Robada"}).status_code == 404


def test_permisos_de_categorias(crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro ve las categorías pero no las modifica."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    marta = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert marta.get(CATS).status_code == 200
    assert marta.post(CATS, json={"nombre": "Nueva"}).status_code == 403
    assert cliente.get(CATS).status_code == 401