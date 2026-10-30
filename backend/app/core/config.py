# backend/app/core/config.py
# Configuración central de Familia Monster. Lee variables de entorno y las valida
# al arrancar: si falta algo crítico o es inseguro en producción, la app no inicia.

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valor de ejemplo del .env.example: jamás debe usarse en producción.
_SECRETO_DE_EJEMPLO = "CAMBIAR_POR_UN_SECRETO"


class Configuracion(BaseSettings):
    """Variables de entorno de la aplicación (sin secretos en el código)."""

    # Lectura desde .env en local; en Vercel vienen del entorno del proyecto.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Identidad y entorno ---
    nombre_app: str = "Familia Monster"
    entorno: Literal["desarrollo", "pruebas", "produccion"] = "desarrollo"

    # --- Base de datos ---
    database_url: str
    database_url_migraciones: str | None = None
    usar_nullpool: bool = True

    # --- Seguridad ---
    secret_key: str = Field(min_length=32)
    algoritmo_jwt: Literal["HS256"] = "HS256"
    minutos_expiracion_acceso: int = Field(default=15, ge=1, le=120)
    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Mostrar la documentación interactiva (/api/docs) aun en producción. Es temporal: se activa para
    # crear el primer hogar y se vuelve a apagar. Por defecto, en producción la documentación no se publica.
    docs_habilitadas: bool = False

    # Token de un solo propósito para crear el primer hogar y administrador.
    # Si no está definido, el endpoint de instalación queda deshabilitado (404).
    setup_token: str | None = Field(default=None, min_length=24)

    # --- CORS (lista separada por comas) ---
    cors_origenes: str = "http://localhost:5173"

    @staticmethod
    def _normalizar_url_bd(url: str) -> str:
        """Fuerza el driver psycopg 3 sin importar cómo entregue la URL el proveedor."""
        for prefijo in ("postgres://", "postgresql://"):
            if url.startswith(prefijo):
                return "postgresql+psycopg://" + url[len(prefijo):]
        return url

    @field_validator("database_url")
    @classmethod
    def _validar_database_url(cls, valor: str) -> str:
        """Acepta solo PostgreSQL y normaliza el driver."""
        normalizada = cls._normalizar_url_bd(valor)
        if not normalizada.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL debe ser una URL de PostgreSQL.")
        return normalizada

    @field_validator("setup_token", mode="before")
    @classmethod
    def _setup_token_vacio_es_none(cls, valor: str | None) -> str | None:
        """Una variable vacía en el .env o en Vercel equivale a 'instalación deshabilitada'."""
        return valor or None

    @field_validator("database_url_migraciones")
    @classmethod
    def _validar_url_migraciones(cls, valor: str | None) -> str | None:
        """Vacío equivale a 'no definida'; si existe, se normaliza igual."""
        if not valor:
            return None
        return cls._normalizar_url_bd(valor)

    @model_validator(mode="after")
    def _validar_produccion(self) -> "Configuracion":
        """Exige controles de seguridad mínimos cuando el entorno es producción."""
        if self.entorno != "produccion":
            return self
        if self.secret_key.startswith(_SECRETO_DE_EJEMPLO):
            raise ValueError("SECRET_KEY no puede ser el valor de ejemplo en producción.")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE debe ser true en producción (HTTPS).")
        for origen in self.cors_origenes_lista:
            if origen == "*" or not origen.startswith("https://"):
                raise ValueError("CORS_ORIGENES debe usar solo URLs https:// explícitas en producción.")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None exige cookie Secure.")
        return self

    @property
    def cors_origenes_lista(self) -> list[str]:
        """Orígenes CORS como lista limpia, sin vacíos."""
        return [o.strip() for o in self.cors_origenes.split(",") if o.strip()]

    @property
    def es_produccion(self) -> bool:
        """Indica si se ejecuta en producción."""
        return self.entorno == "produccion"

    @property
    def docs_visibles(self) -> bool:
        """La documentación interactiva se muestra fuera de producción, o en producción si se habilitó a propósito."""
        return (not self.es_produccion) or self.docs_habilitadas

    @property
    def url_para_migraciones(self) -> str:
        """URL directa para Alembic; si no existe, usa la de la aplicación."""
        return self.database_url_migraciones or self.database_url


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve una única instancia de configuración durante la vida del proceso."""
    return Configuracion()  # type: ignore[call-arg]