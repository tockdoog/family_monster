# backend/app/main.py
# Punto de entrada de la API de Familia Monster. Vercel detecta la variable "app" de este archivo.

import logging
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import obtener_configuracion
from app.core.exceptions import registrar_manejadores_errores, respuesta_error
from app.db.session import obtener_fabrica_sesiones
from app.modules.accounts.router import router as router_cuentas
from app.modules.audit.router import router as router_auditoria
from app.modules.categories.router import router as router_categorias
from app.modules.contributions.router import router as router_aportes
from app.modules.contributions.router import router_reglas as router_reglas_aporte
from app.modules.auth.router import router as router_auth
from app.modules.households.router import router as router_hogares
from app.modules.households.router import router_instalacion
from app.modules.loans.router import router as router_prestamos
from app.modules.members.router import router as router_integrantes
from app.modules.obligations.router import router as router_obligaciones
from app.modules.reports.router import router as router_informes
from app.modules.reports.router import router_tablero
from app.modules.transactions.router import router as router_movimientos

VERSION_API = "0.5.1"

# Registro de eventos técnicos del servicio (los detalles quedan en los logs, nunca en la respuesta).
registro = logging.getLogger("familia_monster.salud")

# Métodos que modifican datos: son los que requieren protección contra CSRF.
_METODOS_CON_CAMBIOS = {"POST", "PUT", "PATCH", "DELETE"}


async def verificar_origen(
    solicitud: Request, siguiente: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Defensa CSRF: bloquea escrituras enviadas desde un sitio no autorizado.

    Los navegadores siempre incluyen la cabecera Origin en solicitudes que modifican datos.
    Se aceptan dos casos: un origen de la lista autorizada (el frontend) o el propio servidor
    (por ejemplo, la documentación interactiva /api/docs). Cualquier otro se rechaza antes de ejecutar nada.
    """
    if solicitud.method in _METODOS_CON_CAMBIOS:
        origen = solicitud.headers.get("origin")
        if origen is not None:
            es_autorizado = origen in obtener_configuracion().cors_origenes_lista
            # Mismo sitio: el origen coincide con el host al que se hizo la solicitud.
            es_mismo_sitio = urlsplit(origen).netloc == solicitud.headers.get("host", "")
            if not (es_autorizado or es_mismo_sitio):
                return respuesta_error(403, "origen_no_permitido", "Origen no autorizado.")
    return await siguiente(solicitud)


async def agregar_cabeceras_seguridad(
    solicitud: Request, siguiente: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Añade cabeceras de seguridad a TODAS las respuestas de la API."""
    cfg = obtener_configuracion()
    respuesta = await siguiente(solicitud)
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if cfg.es_produccion:
        respuesta.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        # Esta política bloquea todo contenido externo y rompería la documentación interactiva, que carga
        # sus scripts desde un CDN: por eso solo se aplica cuando la documentación está oculta.
        if not cfg.docs_visibles:
            respuesta.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return respuesta


def crear_router_v1() -> APIRouter:
    """Router raíz /api/v1: aquí se montan los routers de cada módulo."""
    router = APIRouter(prefix="/api/v1")

    @router.get("/salud", tags=["Sistema"], summary="Estado del servicio")
    async def salud() -> dict[str, str]:
        # No consulta la base de datos ni expone información interna.
        return {"estado": "ok", "version": VERSION_API}

    @router.get("/preparacion", tags=["Sistema"], summary="Disponibilidad real del servicio")
    def preparacion(respuesta: Response) -> dict[str, str]:
        """Comprueba que la API pueda consultar PostgreSQL.

        Responde 200 si la base contesta y 503 si no. El detalle técnico del fallo se guarda
        en los logs del servidor; al cliente solo se le informa el estado general.
        """
        try:
            # Sesión propia (sin la transacción por solicitud): solo se ejecuta una consulta mínima.
            with obtener_fabrica_sesiones()() as sesion:
                sesion.execute(text("SELECT 1"))
        except Exception:
            registro.exception("Falló la comprobación de la base de datos")
            respuesta.status_code = 503
            return {"estado": "degradado", "base_de_datos": "error", "version": VERSION_API}
        return {"estado": "ok", "base_de_datos": "ok", "version": VERSION_API}

    router.include_router(router_instalacion)
    router.include_router(router_auth)
    router.include_router(router_hogares)
    router.include_router(router_integrantes)
    router.include_router(router_cuentas)
    router.include_router(router_categorias)
    router.include_router(router_reglas_aporte)
    router.include_router(router_aportes)
    router.include_router(router_obligaciones)
    router.include_router(router_prestamos)
    router.include_router(router_tablero)
    router.include_router(router_informes)
    router.include_router(router_movimientos)
    router.include_router(router_auditoria)
    return router


def crear_app() -> FastAPI:
    """Fábrica de la aplicación: facilita las pruebas con distintas configuraciones."""
    cfg = obtener_configuracion()

    app = FastAPI(
        title=cfg.nombre_app,
        version=VERSION_API,
        description="API de finanzas del hogar. Montos en pesos colombianos (COP).",
        # En producción no se publica la documentación ni el esquema OpenAPI (salvo DOCS_HABILITADAS=true).
        docs_url="/api/docs" if cfg.docs_visibles else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if cfg.docs_visibles else None,
    )

    # El orden importa: el último agregado es el más externo.
    # CORS restringido a los orígenes autorizados; con credenciales para la cookie de sesión.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origenes_lista,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )
    app.middleware("http")(verificar_origen)
    app.middleware("http")(agregar_cabeceras_seguridad)

    registrar_manejadores_errores(app)
    app.include_router(crear_router_v1())
    return app


# Instancia que importan Vercel y Uvicorn.
app = crear_app()