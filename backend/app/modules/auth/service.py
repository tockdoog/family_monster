# backend/app/modules/auth/service.py
# Reglas de negocio del inicio de sesión: verificación de credenciales y bloqueo por intentos.

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import DemasiadasSolicitudes, NoAutenticado, Prohibido
from app.core.security import (
    crear_token_acceso,
    hashear_contrasena,
    requiere_rehash,
    verificar_contrasena,
)
from app.modules.auth import repository
from app.modules.auth.models import IntentoLogin, Usuario
from app.modules.households.models import Hogar, Membresia

# Política de bloqueo: 5 fallos dentro de 15 minutos bloquean el correo por 15 minutos.
MAXIMO_INTENTOS = 5
VENTANA_INTENTOS = timedelta(minutes=15)
DURACION_BLOQUEO = timedelta(minutes=15)

# Mensaje único para cualquier credencial incorrecta: no revela si el correo existe.
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


@dataclass(frozen=True)
class SesionIniciada:
    """Resultado de un login exitoso."""

    token: str
    usuario: Usuario
    membresia: Membresia
    hogar: Hogar


def _clave_intentos(email: str) -> str:
    """Hash del correo usado como clave del contador (no se guarda el correo en claro)."""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


def _registrar_fallo(intento: IntentoLogin, ahora: datetime) -> None:
    """Suma un fallo y activa el bloqueo al llegar al máximo permitido."""
    if ahora - intento.primer_intento_en > VENTANA_INTENTOS:
        # La ventana anterior ya venció: se empieza a contar de nuevo.
        intento.intentos = 0
        intento.primer_intento_en = ahora
        intento.bloqueado_hasta = None
    intento.intentos += 1
    if intento.intentos >= MAXIMO_INTENTOS:
        intento.bloqueado_hasta = ahora + DURACION_BLOQUEO


def iniciar_sesion(db: Session, email: str, contrasena: str) -> SesionIniciada:
    """Valida credenciales y devuelve un token. Aplica bloqueo por intentos fallidos."""
    ahora = datetime.now(timezone.utc)
    clave = _clave_intentos(email)
    intento = repository.obtener_intento_bloqueando(db, clave, ahora)

    # Si el correo está bloqueado se responde sin verificar la contraseña.
    if intento.bloqueado_hasta and intento.bloqueado_hasta > ahora:
        db.commit()
        raise DemasiadasSolicitudes()

    usuario = repository.usuario_por_email(db, email)
    # Se verifica SIEMPRE (con hash ficticio si no existe) para igualar los tiempos de respuesta.
    contrasena_valida = verificar_contrasena(contrasena, usuario.password_hash if usuario else None)

    if usuario is None or not usuario.activo or not contrasena_valida:
        _registrar_fallo(intento, ahora)
        # El fallo debe persistir aunque se lance una excepción (que normalmente haría rollback).
        db.commit()
        raise NoAutenticado(MENSAJE_CREDENCIALES)

    contexto = repository.contexto_por_usuario_id(db, usuario.id)
    if contexto is None:
        db.commit()
        raise Prohibido("Su cuenta no pertenece a ningún hogar activo.")

    # Login correcto: se limpia el contador y se actualiza el hash si usa parámetros antiguos.
    repository.eliminar_intento(db, clave)
    if requiere_rehash(usuario.password_hash):
        usuario.password_hash = hashear_contrasena(contrasena)

    _, membresia, hogar = contexto
    return SesionIniciada(
        token=crear_token_acceso(usuario.id), usuario=usuario, membresia=membresia, hogar=hogar
    )