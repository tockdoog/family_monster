# backend/tests/modules/test_auth.py
# Pruebas de inicio y cierre de sesión, bloqueo por intentos y validación de la sesión.

import uuid

from sqlalchemy import select, text

from app.core.security import crear_token_acceso
from app.modules.auth.models import IntentoLogin

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
EMAIL = "ana@example.com"
CLAVE = "ClaveSegura2026"


def test_login_correcto_entrega_cookie_httponly_y_datos_sin_hash(crear_hogar, cliente):
    """El login exitoso fija una cookie HttpOnly y nunca devuelve el hash."""
    crear_hogar()
    respuesta = cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE})
    assert respuesta.status_code == 200
    cookie = respuesta.headers["set-cookie"].lower()
    assert "fm_acceso=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "password" not in respuesta.text.lower()
    assert respuesta.json()["rol"] == "admin"
    assert "registrar_movimientos" in respuesta.json()["permisos"]


def test_login_normaliza_mayusculas_del_correo(crear_hogar, cliente):
    """El correo se compara sin distinguir mayúsculas."""
    crear_hogar()
    respuesta = cliente.post(LOGIN, json={"email": "ANA@example.com", "contrasena": CLAVE})
    assert respuesta.status_code == 200


def test_me_devuelve_la_sesion_actual(crear_hogar, cliente, iniciar_sesion):
    """Con sesión válida /me devuelve usuario, hogar y rol."""
    hogar = crear_hogar()
    iniciar_sesion(cliente, EMAIL)
    cuerpo = cliente.get(ME).json()
    assert cuerpo["usuario"]["email"] == EMAIL
    assert cuerpo["hogar"]["id"] == str(hogar.id)


def test_credenciales_incorrectas_no_revelan_si_el_correo_existe(crear_hogar, cliente):
    """Contraseña errónea y correo inexistente producen la misma respuesta exacta."""
    crear_hogar()
    mala_clave = cliente.post(LOGIN, json={"email": EMAIL, "contrasena": "Equivocada12345"})
    no_existe = cliente.post(LOGIN, json={"email": "nadie@example.com", "contrasena": "Equivocada12345"})
    assert mala_clave.status_code == no_existe.status_code == 401
    assert mala_clave.json() == no_existe.json()
    assert mala_clave.json()["error"]["mensaje"] == "Correo o contraseña incorrectos."


def test_cinco_fallos_bloquean_incluso_con_la_clave_correcta(crear_hogar, sesion, cliente):
    """Tras 5 fallos el correo queda bloqueado (429) y la clave correcta tampoco entra."""
    crear_hogar()
    for _ in range(5):
        assert cliente.post(LOGIN, json={"email": EMAIL, "contrasena": "Equivocada12345"}).status_code == 401
    bloqueado = cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE})
    assert bloqueado.status_code == 429
    # El contador guarda un hash, nunca el correo en claro.
    clave = sesion.execute(select(IntentoLogin.clave)).scalar_one()
    assert EMAIL not in clave and len(clave) == 64


def test_el_bloqueo_tambien_aplica_a_correos_inexistentes(bd, cliente):
    """Un atacante no puede distinguir cuentas reales de falsas por el bloqueo."""
    for _ in range(5):
        cliente.post(LOGIN, json={"email": "fantasma@example.com", "contrasena": "Equivocada12345"})
    respuesta = cliente.post(LOGIN, json={"email": "fantasma@example.com", "contrasena": "Equivocada12345"})
    assert respuesta.status_code == 429


def test_un_login_correcto_reinicia_el_contador(crear_hogar, sesion, cliente):
    """Fallos no consecutivos no bloquean: el éxito borra el contador."""
    crear_hogar()
    for _ in range(3):
        cliente.post(LOGIN, json={"email": EMAIL, "contrasena": "Equivocada12345"})
    assert cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE}).status_code == 200
    assert sesion.execute(select(IntentoLogin)).first() is None
    for _ in range(4):
        assert cliente.post(LOGIN, json={"email": EMAIL, "contrasena": "Equivocada12345"}).status_code == 401


def test_me_sin_cookie_o_con_cookie_falsa_es_401(bd, cliente):
    """Sin sesión o con un token inválido no se accede."""
    assert cliente.get(ME).status_code == 401
    cliente.cookies.set("fm_acceso", "token.falso.invalido")
    assert cliente.get(ME).status_code == 401


def test_token_valido_de_usuario_inexistente_es_401(bd, cliente):
    """Un token bien firmado de un usuario que no existe no da acceso."""
    cliente.cookies.set("fm_acceso", crear_token_acceso(uuid.uuid4()))
    assert cliente.get(ME).status_code == 401


def test_logout_elimina_la_sesion(crear_hogar, cliente, iniciar_sesion):
    """Tras cerrar sesión /me vuelve a exigir autenticación."""
    crear_hogar()
    iniciar_sesion(cliente, EMAIL)
    assert cliente.post("/api/v1/auth/logout").status_code == 204
    assert cliente.get(ME).status_code == 401


def test_usuario_desactivado_pierde_acceso_aunque_su_token_siga_vigente(
    crear_hogar, sesion, cliente, iniciar_sesion
):
    """Desactivar un usuario corta su sesión de inmediato y bloquea nuevos logins."""
    crear_hogar()
    iniciar_sesion(cliente, EMAIL)
    sesion.execute(text("UPDATE users SET activo = false"))
    sesion.commit()
    assert cliente.get(ME).status_code == 401
    assert cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE}).status_code == 401


def test_usuario_sin_membresia_activa_no_puede_entrar(crear_hogar, sesion, cliente):
    """Sin hogar activo el login es rechazado con 403."""
    crear_hogar()
    sesion.execute(text("UPDATE memberships SET activo = false"))
    sesion.commit()
    assert cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE}).status_code == 403


def test_campos_desconocidos_en_el_login_se_rechazan(bd, cliente):
    """El contrato es estricto: no se aceptan campos extra."""
    respuesta = cliente.post(LOGIN, json={"email": EMAIL, "contrasena": CLAVE, "rol": "admin"})
    assert respuesta.status_code == 422


def test_escritura_desde_origen_no_autorizado_se_bloquea_por_csrf(crear_hogar, cliente):
    """Un POST con Origin ajeno se rechaza antes de procesarse."""
    crear_hogar()
    ajeno = cliente.post(
        LOGIN, json={"email": EMAIL, "contrasena": CLAVE}, headers={"Origin": "https://sitio-malicioso.com"}
    )
    assert ajeno.status_code == 403
    assert ajeno.json()["error"]["codigo"] == "origen_no_permitido"
    propio = cliente.post(
        LOGIN, json={"email": EMAIL, "contrasena": CLAVE}, headers={"Origin": "http://localhost:5173"}
    )
    assert propio.status_code == 200


def test_la_documentacion_interactiva_puede_escribir_desde_el_mismo_sitio(crear_hogar, cliente):
    """Un Origin igual al host del servidor (como envía /api/docs) es del mismo sitio y se acepta;
    uno que solo se le parece (otro puerto o dominio) se sigue rechazando."""
    crear_hogar()
    cuerpo = {"email": EMAIL, "contrasena": CLAVE}
    mismo_sitio = cliente.post(LOGIN, json=cuerpo, headers={"Origin": "http://testserver"})
    assert mismo_sitio.status_code == 200
    parecido = cliente.post(LOGIN, json=cuerpo, headers={"Origin": "http://testserver:9999"})
    assert parecido.status_code == 403
    disfrazado = cliente.post(LOGIN, json=cuerpo, headers={"Origin": "http://testserver.malicioso.com"})
    assert disfrazado.status_code == 403