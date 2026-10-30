# backend/tests/conftest.py
# Preparación común de pruebas. Define variables de entorno de prueba ANTES de importar la app,
# prepara una base PostgreSQL aislada con las migraciones reales y ofrece fábricas de datos.

import os
from collections.abc import Callable, Iterator
from pathlib import Path

# Entorno aislado: nunca usa secretos reales. La base de pruebas se puede cambiar con TEST_DATABASE_URL.
os.environ["ENTORNO"] = "pruebas"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/familia_monster_prueba"
)
os.environ["SECRET_KEY"] = "clave-solo-para-pruebas-de-al-menos-32-caracteres"
os.environ["SETUP_TOKEN"] = "token-de-instalacion-para-pruebas-123456"
os.environ["COOKIE_SECURE"] = "false"
os.environ["CORS_ORIGENES"] = "http://localhost:5173"
os.environ.pop("DATABASE_URL_MIGRACIONES", None)

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import obtener_configuracion
from app.db.session import obtener_fabrica_sesiones
from app.main import crear_app
from app.modules.households.models import Hogar, Membresia
from app.modules.households.service import crear_hogar_con_admin
from app.modules.members import service as servicio_integrantes

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
CLAVE_VALIDA = "ClaveSegura2026"


@pytest.fixture(autouse=True)
def limpiar_cache_configuracion():
    """Garantiza que cada prueba lea la configuración desde cero."""
    obtener_configuracion.cache_clear()
    yield
    obtener_configuracion.cache_clear()


@pytest.fixture
def cliente() -> TestClient:
    """Cliente HTTP de prueba sobre una aplicación nueva."""
    return TestClient(crear_app(), raise_server_exceptions=False)


@pytest.fixture(scope="session")
def esquema_bd() -> None:
    """Recrea el esquema con las migraciones reales (también prueba que se puedan revertir)."""
    url = obtener_configuracion().database_url
    nombre_bd = url.rsplit("/", 1)[-1].split("?")[0]
    # Protección: estas pruebas borran datos, así que solo corren contra bases cuyo nombre termina en _prueba.
    if not nombre_bd.endswith("_prueba"):
        pytest.exit(f"Por seguridad, la base de pruebas debe terminar en '_prueba' (actual: {nombre_bd}).")
    try:
        motor = create_engine(url)
        with motor.connect():
            pass
    except OperationalError:
        pytest.skip("PostgreSQL de pruebas no disponible: se omiten las pruebas con base de datos.")

    # Los datos que dejó una corrida anterior se vacían antes de bajar las migraciones: una migración
    # no puede revertirse mientras existan movimientos de los tipos que ella introdujo (a propósito).
    with motor.begin() as conexion:
        tablas = conexion.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        ).scalars().all()
        if tablas:
            conexion.execute(text("TRUNCATE TABLE " + ", ".join(f'"{t}"' for t in tablas) + " RESTART IDENTITY CASCADE"))

    config = Config(str(RAIZ_BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    motor.dispose()


@pytest.fixture
def bd(esquema_bd) -> None:
    """Deja todas las tablas vacías antes de cada prueba que usa base de datos."""
    motor = create_engine(obtener_configuracion().database_url)
    with motor.begin() as conexion:
        conexion.execute(
            text(
                "TRUNCATE TABLE audit_logs, contribution_shares, contribution_rule_items, "
                "contribution_rules, obligation_payments, obligations, installment_payments, "
                "installments, loans, transaction_lines, transactions, categories, accounts, "
                "members, memberships, users, households, login_attempts "
                "RESTART IDENTITY CASCADE"
            )
        )
    motor.dispose()


@pytest.fixture
def sesion(bd) -> Iterator[Session]:
    """Sesión directa a la base para preparar y verificar datos."""
    sesion_bd = obtener_fabrica_sesiones()()
    yield sesion_bd
    sesion_bd.rollback()
    sesion_bd.close()


@pytest.fixture
def crear_hogar(sesion: Session) -> Callable[..., Hogar]:
    """Fábrica de hogares con su administrador (devuelve el hogar creado)."""

    def _crear(
        nombre_hogar: str = "Hogar Monster",
        email: str = "ana@example.com",
        nombre: str = "Ana Admin",
        contrasena: str = CLAVE_VALIDA,
    ) -> Hogar:
        hogar = crear_hogar_con_admin(
            sesion,
            nombre_hogar=nombre_hogar,
            nombre_completo=nombre,
            email=email,
            contrasena=contrasena,
        )
        sesion.commit()
        return hogar

    return _crear


@pytest.fixture
def crear_miembro(sesion: Session) -> Callable[..., None]:
    """Fábrica de integrantes con acceso a la aplicación dentro de un hogar."""

    def _crear(hogar: Hogar, nombre: str, email: str, rol: str = "miembro") -> None:
        # Quien actúa es el administrador del hogar.
        admin_id = sesion.execute(
            select(Membresia.user_id).where(Membresia.household_id == hogar.id, Membresia.rol == "admin")
        ).scalar_one()
        integrante = servicio_integrantes.crear_integrante(sesion, hogar.id, admin_id, nombre)
        servicio_integrantes.otorgar_acceso(
            sesion, hogar.id, admin_id, integrante.id, email=email, contrasena=CLAVE_VALIDA, rol=rol
        )
        sesion.commit()

    return _crear


@pytest.fixture
def nuevo_cliente() -> Callable[[], TestClient]:
    """Fábrica de clientes independientes (cada uno con su propia cookie de sesión)."""
    return lambda: TestClient(crear_app(), raise_server_exceptions=False)


@pytest.fixture
def iniciar_sesion() -> Callable[..., TestClient]:
    """Inicia sesión en un cliente y verifica que haya sido exitosa."""

    def _login(cliente: TestClient, email: str, contrasena: str = CLAVE_VALIDA) -> TestClient:
        respuesta = cliente.post("/api/v1/auth/login", json={"email": email, "contrasena": contrasena})
        assert respuesta.status_code == 200, respuesta.text
        return cliente

    return _login