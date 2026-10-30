# backend/tests/modules/test_integrantes.py
# Pruebas de integrantes: permisos por rol, aislamiento entre hogares y transacciones.

import pytest
from sqlalchemy import select

from app.modules.auth.models import Usuario
from app.modules.households import repository as repo_hogares
from app.modules.members.models import Integrante

MEMBERS = "/api/v1/members"
CLAVE = "ClaveSegura2026"


def _acceso(email: str, contrasena: str = CLAVE, rol: str = "miembro") -> dict:
    """Cuerpo para otorgar acceso a un integrante."""
    return {"email": email, "contrasena": contrasena, "rol": rol}


def test_sin_sesion_no_se_puede_consultar_integrantes(bd, cliente):
    """Los endpoints protegidos exigen autenticación."""
    assert cliente.get(MEMBERS).status_code == 401
    assert cliente.post(MEMBERS, json={"nombre": "Luis"}).status_code == 401


def test_admin_crea_y_lista_integrantes(crear_hogar, cliente, iniciar_sesion):
    """El administrador registra integrantes y aparecen en el listado."""
    crear_hogar()
    iniciar_sesion(cliente, "ana@example.com")
    creado = cliente.post(MEMBERS, json={"nombre": "  Luis Monster  "})
    assert creado.status_code == 201
    assert creado.json()["nombre"] == "Luis Monster"
    assert creado.json()["tiene_acceso"] is False
    nombres = [i["nombre"] for i in cliente.get(MEMBERS).json()]
    assert nombres == ["Ana Admin", "Luis Monster"]


def test_nombre_duplicado_en_el_hogar_se_rechaza_sin_distinguir_mayusculas(
    crear_hogar, cliente, iniciar_sesion
):
    """No se repiten nombres dentro del mismo hogar."""
    crear_hogar()
    iniciar_sesion(cliente, "ana@example.com")
    assert cliente.post(MEMBERS, json={"nombre": "Luis"}).status_code == 201
    assert cliente.post(MEMBERS, json={"nombre": "LUIS"}).status_code == 409


def test_miembro_puede_consultar_pero_no_modificar(
    crear_hogar, crear_miembro, nuevo_cliente, iniciar_sesion
):
    """El rol miembro es de solo lectura: el backend responde 403 al intentar modificar."""
    hogar = crear_hogar()
    crear_miembro(hogar, "Marta Miembro", "marta@example.com")
    cliente = iniciar_sesion(nuevo_cliente(), "marta@example.com")
    assert cliente.get(MEMBERS).status_code == 200
    assert cliente.post(MEMBERS, json={"nombre": "Intruso"}).status_code == 403
    assert (
        cliente.post(f"{MEMBERS}/{hogar.id}/acceso", json=_acceso("x@example.com")).status_code == 403
    )


def test_admin_otorga_acceso_y_el_nuevo_usuario_puede_entrar(
    crear_hogar, nuevo_cliente, iniciar_sesion
):
    """El integrante con acceso inicia sesión con el rol asignado."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    luis = admin.post(MEMBERS, json={"nombre": "Luis"}).json()
    respuesta = admin.post(f"{MEMBERS}/{luis['id']}/acceso", json=_acceso("Luis@example.com"))
    assert respuesta.status_code == 201
    assert respuesta.json()["tiene_acceso"] is True and respuesta.json()["rol"] == "miembro"
    sesion_luis = iniciar_sesion(nuevo_cliente(), "luis@example.com")
    assert sesion_luis.get("/api/v1/auth/me").json()["rol"] == "miembro"


def test_otorgar_acceso_con_contrasena_debil_no_deja_rastro(
    crear_hogar, sesion, nuevo_cliente, iniciar_sesion
):
    """Una contraseña débil se rechaza y el integrante sigue sin acceso."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    luis = admin.post(MEMBERS, json={"nombre": "Luis"}).json()
    respuesta = admin.post(f"{MEMBERS}/{luis['id']}/acceso", json=_acceso("luis@example.com", "corta1"))
    assert respuesta.status_code == 422
    assert sesion.execute(select(Usuario).where(Usuario.email == "luis@example.com")).first() is None


def test_correo_repetido_y_doble_acceso_dan_conflicto(crear_hogar, nuevo_cliente, iniciar_sesion):
    """No se repite un correo ni se otorga acceso dos veces al mismo integrante."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    luis = admin.post(MEMBERS, json={"nombre": "Luis"}).json()
    sofia = admin.post(MEMBERS, json={"nombre": "Sofía"}).json()
    assert admin.post(f"{MEMBERS}/{luis['id']}/acceso", json=_acceso("luis@example.com")).status_code == 201
    assert admin.post(f"{MEMBERS}/{luis['id']}/acceso", json=_acceso("otro@example.com")).status_code == 409
    assert admin.post(f"{MEMBERS}/{sofia['id']}/acceso", json=_acceso("luis@example.com")).status_code == 409


def test_un_hogar_no_ve_ni_modifica_integrantes_de_otro_hogar(
    crear_hogar, nuevo_cliente, iniciar_sesion
):
    """Aislamiento horizontal: el hogar B no accede a nada del hogar A."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    luis_a = admin_a.post(MEMBERS, json={"nombre": "Luis de A"}).json()

    nombres_b = [i["nombre"] for i in admin_b.get(MEMBERS).json()]
    assert nombres_b == ["Beto Admin"]
    # Intentar dar acceso a un integrante ajeno responde como si no existiera.
    intento = admin_b.post(f"{MEMBERS}/{luis_a['id']}/acceso", json=_acceso("robo@example.com"))
    assert intento.status_code == 404
    assert admin_b.get("/api/v1/households/current").json()["nombre"] == "Hogar B"
    assert admin_a.get("/api/v1/households/current").json()["nombre"] == "Hogar A"


def test_el_mismo_nombre_puede_existir_en_hogares_distintos(
    crear_hogar, nuevo_cliente, iniciar_sesion
):
    """La unicidad del nombre es por hogar, no global."""
    crear_hogar("Hogar A", "ana@example.com", "Ana Admin")
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_a = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    assert admin_a.post(MEMBERS, json={"nombre": "Luis"}).status_code == 201
    assert admin_b.post(MEMBERS, json={"nombre": "Luis"}).status_code == 201


def test_identificador_de_integrante_con_formato_invalido_da_422(
    crear_hogar, nuevo_cliente, iniciar_sesion
):
    """Un id que no es UUID se rechaza en la validación de entrada."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    assert admin.post(f"{MEMBERS}/123/acceso", json=_acceso("x@example.com")).status_code == 422


def test_si_falla_a_mitad_de_la_operacion_se_revierte_todo(
    crear_hogar, sesion, nuevo_cliente, iniciar_sesion, monkeypatch
):
    """Si falla la creación de la membresía, tampoco queda el usuario creado antes (transacción atómica)."""
    crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), "ana@example.com")
    luis = admin.post(MEMBERS, json={"nombre": "Luis"}).json()

    def _falla(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(repo_hogares, "crear_membresia", _falla)
    respuesta = admin.post(f"{MEMBERS}/{luis['id']}/acceso", json=_acceso("luis@example.com"))
    assert respuesta.status_code == 500
    assert respuesta.json()["error"]["codigo"] == "error_interno"
    assert "fallo simulado" not in respuesta.text
    assert sesion.execute(select(Usuario).where(Usuario.email == "luis@example.com")).first() is None
    luis_bd = sesion.execute(select(Integrante).where(Integrante.nombre == "Luis")).scalar_one()
    assert luis_bd.user_id is None