# backend/app/core/exceptions.py
# Errores de la aplicación y manejadores globales. Todas las respuestas de error
# tienen el mismo formato: {"error": {"codigo", "mensaje", "detalle"}} y están en español.

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

registro = logging.getLogger("familia_monster.errores")


# ---------------------------------------------------------------------------
# Jerarquía de errores de negocio
# ---------------------------------------------------------------------------
class ErrorAplicacion(Exception):
    """Base de todos los errores controlados de la aplicación."""

    status_code: int = 500
    codigo: str = "error_interno"
    mensaje_por_defecto: str = "Ocurrió un error inesperado."

    def __init__(self, mensaje: str | None = None, *, detalle: Any = None) -> None:
        self.mensaje = mensaje or self.mensaje_por_defecto
        self.detalle = detalle
        super().__init__(self.mensaje)


class ErrorNegocio(ErrorAplicacion):
    """Una regla de negocio impide completar la operación."""

    status_code = 422
    codigo = "regla_de_negocio"
    mensaje_por_defecto = "La operación no cumple las reglas del hogar."


class NoAutenticado(ErrorAplicacion):
    """Credenciales ausentes, inválidas o vencidas."""

    status_code = 401
    codigo = "no_autenticado"
    mensaje_por_defecto = "Debe iniciar sesión para continuar."


class Prohibido(ErrorAplicacion):
    """El usuario está autenticado pero no tiene permiso."""

    status_code = 403
    codigo = "prohibido"
    mensaje_por_defecto = "No tiene permiso para realizar esta acción."


class NoEncontrado(ErrorAplicacion):
    """El recurso no existe o pertenece a otro hogar (no se distingue a propósito)."""

    status_code = 404
    codigo = "no_encontrado"
    mensaje_por_defecto = "El recurso solicitado no existe."


class DemasiadasSolicitudes(ErrorAplicacion):
    """Se superó el límite de intentos permitido."""

    status_code = 429
    codigo = "demasiadas_solicitudes"
    mensaje_por_defecto = "Demasiados intentos. Intente de nuevo en unos minutos."


class Conflicto(ErrorAplicacion):
    """La operación choca con el estado actual (por ejemplo, un duplicado)."""

    status_code = 409
    codigo = "conflicto"
    mensaje_por_defecto = "La operación entra en conflicto con el estado actual."


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
# Traducción de los tipos de error de Pydantic más comunes.
_MENSAJES_VALIDACION = {
    "missing": "Este campo es obligatorio.",
    "string_too_short": "El texto es demasiado corto.",
    "string_too_long": "El texto es demasiado largo.",
    "greater_than": "El valor es demasiado bajo.",
    "greater_than_equal": "El valor es demasiado bajo.",
    "less_than": "El valor es demasiado alto.",
    "less_than_equal": "El valor es demasiado alto.",
    "decimal_parsing": "Importe no válido.",
    "uuid_parsing": "Identificador no válido.",
    "enum": "Valor no permitido.",
    "json_invalid": "El cuerpo de la solicitud no es un JSON válido.",
}

# Mensajes para errores HTTP genéricos del framework.
_MENSAJES_HTTP = {
    401: "Debe iniciar sesión para continuar.",
    403: "No tiene permiso para realizar esta acción.",
    404: "El recurso solicitado no existe.",
    405: "Método no permitido.",
    429: "Demasiadas solicitudes. Intente de nuevo en unos minutos.",
}


def respuesta_error(status: int, codigo: str, mensaje: str, detalle: Any = None) -> JSONResponse:
    """Construye la respuesta de error con el formato único de la API."""
    return JSONResponse(
        status_code=status,
        content={"error": {"codigo": codigo, "mensaje": mensaje, "detalle": detalle}},
    )


# ---------------------------------------------------------------------------
# Registro de manejadores en la aplicación
# ---------------------------------------------------------------------------
def registrar_manejadores_errores(app: FastAPI) -> None:
    """Conecta los manejadores globales para que ningún error filtre información interna."""

    @app.exception_handler(ErrorAplicacion)
    async def _manejar_error_aplicacion(_: Request, exc: ErrorAplicacion) -> JSONResponse:
        # Errores esperados: se devuelven tal cual, con su código y mensaje.
        return respuesta_error(exc.status_code, exc.codigo, exc.mensaje, exc.detalle)

    @app.exception_handler(RequestValidationError)
    async def _manejar_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Nunca se devuelve el valor recibido (podría ser una contraseña); solo campo y motivo.
        detalle = [
            {
                "campo": ".".join(str(p) for p in e["loc"] if p != "body"),
                "mensaje": _MENSAJES_VALIDACION.get(e["type"], "Valor no válido."),
            }
            for e in exc.errors()
        ]
        return respuesta_error(422, "validacion", "Hay datos que no son válidos.", detalle)

    @app.exception_handler(StarletteHTTPException)
    async def _manejar_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Rutas inexistentes, métodos no permitidos, etc.
        mensaje = _MENSAJES_HTTP.get(exc.status_code, "No fue posible procesar la solicitud.")
        return respuesta_error(exc.status_code, f"http_{exc.status_code}", mensaje)

    @app.exception_handler(Exception)
    async def _manejar_inesperado(_: Request, exc: Exception) -> JSONResponse:
        # Se registra el detalle técnico en el servidor, pero al cliente solo un mensaje genérico.
        registro.exception("Error no controlado", exc_info=exc)
        return respuesta_error(500, "error_interno", "Ocurrió un error inesperado.")