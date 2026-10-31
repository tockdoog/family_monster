# backend/migrations/env.py
# Entorno de ejecución de Alembic. Usa la URL directa (sin pooler) para migrar y
# descubre automáticamente los modelos de cada módulo en app/modules/*/models.py.

import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.modules as paquete_modulos
from app.core.config import obtener_configuracion
from app.db.base import Base

# Configuración de Alembic y de sus logs.
config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False: Alembic no debe silenciar los registros de la aplicación
    # (por ejemplo, el de errores 500), que ya existen cuando se ejecutan las migraciones desde las pruebas.
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def importar_modelos() -> None:
    """Importa models.py de cada módulo para que sus tablas queden en Base.metadata."""
    for modulo in pkgutil.iter_modules(paquete_modulos.__path__):
        nombre = f"app.modules.{modulo.name}.models"
        try:
            importlib.import_module(nombre)
        except ModuleNotFoundError as error:
            # Se ignora solo si el módulo aún no tiene models.py; cualquier otro fallo se propaga.
            if error.name != nombre:
                raise


importar_modelos()
target_metadata = Base.metadata


def ejecutar_migraciones_sin_conexion() -> None:
    """Modo 'offline': genera el SQL sin conectarse a la base de datos."""
    context.configure(
        url=obtener_configuracion().url_para_migraciones,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_migraciones_con_conexion() -> None:
    """Modo 'online': aplica las migraciones dentro de una transacción."""
    motor = create_engine(obtener_configuracion().url_para_migraciones, poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# Alembic decide el modo según cómo se invoque el comando.
if context.is_offline_mode():
    ejecutar_migraciones_sin_conexion()
else:
    ejecutar_migraciones_con_conexion()