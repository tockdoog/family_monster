# backend/app/core/security.py
# Núcleo criptográfico: hash de contraseñas (Argon2id), política de contraseñas,
# tokens JWT de vida corta y cookie de sesión HttpOnly.

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response

from app.core.config import obtener_configuracion
from app.core.exceptions import ErrorNegocio, NoAutenticado

# Nombre de la cookie que transporta el token de acceso.
NOMBRE_COOKIE_ACCESO = "fm_acceso"

# Tipo de token: evita que un token de otro propósito sirva como token de acceso.
_TIPO_TOKEN_ACCESO = "acceso"

# ---------------------------------------------------------------------------
# Hash de contraseñas
# ---------------------------------------------------------------------------
# Argon2id con 64 MiB de memoria: resistente a GPU y viable en funciones serverless.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

# Hash falso para igualar tiempos cuando el usuario no existe (evita enumerar correos).
_HASH_FICTICIO = _hasher.hash("contrasena-ficticia-no-valida")


def hashear_contrasena(contrasena: str) -> str:
    """Devuelve el hash Argon2id (incluye sal aleatoria) de una contraseña."""
    return _hasher.hash(contrasena)


def verificar_contrasena(contrasena: str, hash_almacenado: str | None) -> bool:
    """Compara una contraseña con su hash; si no hay hash, gasta el mismo tiempo y falla."""
    objetivo = hash_almacenado or _HASH_FICTICIO
    try:
        coincide = _hasher.verify(objetivo, contrasena)
    except (VerificationError, InvalidHashError):
        return False
    # Si no había hash real, el resultado nunca puede ser positivo.
    return coincide and hash_almacenado is not None


def requiere_rehash(hash_almacenado: str) -> bool:
    """Indica si el hash usa parámetros antiguos y conviene regenerarlo al iniciar sesión."""
    return _hasher.check_needs_rehash(hash_almacenado)


# ---------------------------------------------------------------------------
# Política de contraseñas
# ---------------------------------------------------------------------------
_LONGITUD_MINIMA = 12
_LONGITUD_MAXIMA = 128


def validar_politica_contrasena(contrasena: str) -> None:
    """Lanza ErrorNegocio si la contraseña no cumple la política mínima."""
    problemas: list[str] = []
    if len(contrasena) < _LONGITUD_MINIMA:
        problemas.append(f"Debe tener al menos {_LONGITUD_MINIMA} caracteres.")
    if len(contrasena) > _LONGITUD_MAXIMA:
        problemas.append(f"No puede superar {_LONGITUD_MAXIMA} caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", contrasena):
        problemas.append("Debe incluir al menos una letra.")
    if not re.search(r"\d", contrasena):
        problemas.append("Debe incluir al menos un número.")
    if problemas:
        raise ErrorNegocio("La contraseña no cumple la política de seguridad.", detalle=problemas)


# ---------------------------------------------------------------------------
# Tokens de acceso (JWT)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatosToken:
    """Datos ya verificados de un token de acceso."""

    usuario_id: str
    jti: str
    expira_en: datetime


def crear_token_acceso(usuario_id: uuid.UUID | str) -> str:
    """Firma un token de vida corta. El hogar NO va en el token: se consulta siempre en base de datos."""
    cfg = obtener_configuracion()
    ahora = datetime.now(timezone.utc)
    carga = {
        "sub": str(usuario_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=cfg.minutos_expiracion_acceso),
        "jti": uuid.uuid4().hex,
        "typ": _TIPO_TOKEN_ACCESO,
    }
    return jwt.encode(carga, cfg.secret_key, algorithm=cfg.algoritmo_jwt)


def decodificar_token_acceso(token: str) -> DatosToken:
    """Valida firma, vigencia y tipo del token; cualquier fallo es 'no autenticado'."""
    cfg = obtener_configuracion()
    try:
        carga = jwt.decode(
            token,
            cfg.secret_key,
            algorithms=[cfg.algoritmo_jwt],  # lista fija: bloquea alg=none y confusión de algoritmos
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise NoAutenticado("La sesión no es válida o ya venció.") from exc

    if carga.get("typ") != _TIPO_TOKEN_ACCESO:
        raise NoAutenticado("La sesión no es válida o ya venció.")

    return DatosToken(
        usuario_id=carga["sub"],
        jti=carga["jti"],
        expira_en=datetime.fromtimestamp(carga["exp"], tz=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Cookie de sesión
# ---------------------------------------------------------------------------
def establecer_cookie_acceso(respuesta: Response, token: str) -> None:
    """Guarda el token en una cookie HttpOnly (inaccesible para JavaScript)."""
    cfg = obtener_configuracion()
    respuesta.set_cookie(
        key=NOMBRE_COOKIE_ACCESO,
        value=token,
        max_age=cfg.minutos_expiracion_acceso * 60,
        httponly=True,
        secure=cfg.cookie_secure,
        samesite=cfg.cookie_samesite,
        path="/",
    )


def eliminar_cookie_acceso(respuesta: Response) -> None:
    """Borra la cookie de sesión al cerrar sesión, con los mismos atributos de seguridad."""
    cfg = obtener_configuracion()
    respuesta.delete_cookie(
        key=NOMBRE_COOKIE_ACCESO,
        path="/",
        httponly=True,
        secure=cfg.cookie_secure,
        samesite=cfg.cookie_samesite,
    )