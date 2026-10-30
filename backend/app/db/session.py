# backend/app/db/session.py
# Motor y sesiones de SQLAlchemy. Se crean de forma perezosa (al primer uso) y están
# preparados para Vercel: sin pool persistente y compatibles con el pooler de Neon/Supabase.

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import obtener_configuracion


@lru_cache
def obtener_engine() -> Engine:
    """Crea el motor una sola vez por proceso."""
    cfg = obtener_configuracion()
    opciones: dict = {
        "pool_pre_ping": True,
        # El pooler en modo transacción (pgbouncer) no admite sentencias preparadas del servidor.
        # Además se limita la espera al conectar: una base en reposo (Neon) puede tardar unos segundos en despertar.
        "connect_args": {"prepare_threshold": None, "connect_timeout": 15},
    }
    if cfg.usar_nullpool:
        # Serverless: cada invocación abre y cierra su conexión; el pooler externo la reutiliza.
        opciones["poolclass"] = NullPool
    else:
        # Servidor tradicional: pool pequeño y acotado.
        opciones.update(pool_size=5, max_overflow=5, pool_recycle=1800)
    return create_engine(cfg.database_url, **opciones)


@lru_cache
def obtener_fabrica_sesiones() -> sessionmaker[Session]:
    """Fábrica de sesiones; sin autoflush ni expiración para tener un control explícito."""
    return sessionmaker(bind=obtener_engine(), autoflush=False, expire_on_commit=False)


def obtener_bd() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por solicitud, con transacción atómica.

    Si la solicitud termina bien se confirma (commit); si ocurre cualquier error se
    revierte todo (rollback). Así una operación con varios registros nunca queda a medias.
    """
    sesion = obtener_fabrica_sesiones()()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()


# Sesión inyectable en los endpoints. scope="function" hace que el commit ocurra ANTES de
# enviar la respuesta: si confirmar falla, el cliente recibe un error y no un falso "éxito".
SesionBD = Annotated[Session, Depends(obtener_bd, scope="function")]