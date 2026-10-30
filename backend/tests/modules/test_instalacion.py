# backend/tests/modules/test_instalacion.py
# Pruebas de la instalación inicial: token, una sola vez y atomicidad.

from sqlalchemy import func, select

from app.core.config import obtener_configuracion
from app.modules.auth.models import Usuario
from app.modules.households.models import Hogar
from app.modules.members.models import Integrante

URL = "/api/v1/instalacion"
TOKEN = {"X-Setup-Token": "token-de-instalacion-para-pruebas-123456"}
DATOS = {
    "nombre_hogar": "Familia Monster",
    "nombre_completo": "Ana Administradora",
    "email": "Ana@example.com",
    "contrasena": "ClaveSegura2026",
}


def _contar(sesion, modelo) -> int:
    """Cantidad de filas de una tabla."""
    return sesion.execute(select(func.count()).select_from(modelo)).scalar_one()


def test_sin_setup_token_configurado_el_endpoint_no_existe(bd, cliente, monkeypatch):
    """Sin SETUP_TOKEN la instalación está deshabilitada y responde 404."""
    monkeypatch.delenv("SETUP_TOKEN")
    # La configuración ya se había leído al crear el cliente: se descarta para que lea el entorno nuevo.
    obtener_configuracion.cache_clear()
    assert cliente.post(URL, json=DATOS, headers=TOKEN).status_code == 404


def test_token_incorrecto_o_ausente_es_rechazado_y_no_crea_nada(sesion, cliente):
    """Un token erróneo o faltante responde 403 y no deja ningún dato."""
    assert cliente.post(URL, json=DATOS, headers={"X-Setup-Token": "incorrecto"}).status_code == 403
    assert cliente.post(URL, json=DATOS).status_code == 403
    assert _contar(sesion, Usuario) == 0
    assert _contar(sesion, Hogar) == 0


def test_instalacion_correcta_crea_hogar_admin_e_integrante(sesion, cliente):
    """Crea hogar COP, usuario admin con correo en minúsculas e integrante vinculado."""
    respuesta = cliente.post(URL, json=DATOS, headers=TOKEN)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["moneda"] == "COP"
    assert cuerpo["zona_horaria"] == "America/Bogota"

    usuario = sesion.execute(select(Usuario)).scalar_one()
    assert usuario.email == "ana@example.com"
    assert usuario.password_hash.startswith("$argon2id$")
    integrante = sesion.execute(select(Integrante)).scalar_one()
    assert integrante.user_id == usuario.id


def test_el_admin_instalado_puede_iniciar_sesion(bd, cliente):
    """Tras instalar, el administrador entra con su rol de admin."""
    cliente.post(URL, json=DATOS, headers=TOKEN)
    respuesta = cliente.post(
        "/api/v1/auth/login", json={"email": "ana@example.com", "contrasena": "ClaveSegura2026"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "admin"


def test_la_instalacion_solo_funciona_una_vez(sesion, cliente):
    """Una segunda instalación responde 409 y no crea otro hogar."""
    assert cliente.post(URL, json=DATOS, headers=TOKEN).status_code == 201
    otra = {**DATOS, "email": "otra@example.com"}
    respuesta = cliente.post(URL, json=otra, headers=TOKEN)
    assert respuesta.status_code == 409
    assert _contar(sesion, Hogar) == 1


def test_contrasena_debil_se_rechaza_sin_crear_nada(sesion, cliente):
    """La política de contraseñas se aplica y no queda un hogar a medias."""
    respuesta = cliente.post(URL, json={**DATOS, "contrasena": "corta1"}, headers=TOKEN)
    assert respuesta.status_code == 422
    assert _contar(sesion, Hogar) == 0
    assert _contar(sesion, Usuario) == 0


def test_correo_invalido_se_rechaza(bd, cliente):
    """Un correo mal formado devuelve 422 con mensaje en español."""
    respuesta = cliente.post(URL, json={**DATOS, "email": "no-es-correo"}, headers=TOKEN)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "validacion"