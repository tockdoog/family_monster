# backend/app/modules/categories/service.py
# Reglas de negocio de categorías: siembra inicial, alta, renombrado y desactivación.

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, NoEncontrado
from app.modules.audit import service as auditoria
from app.modules.categories import repository
from app.modules.categories.models import Categoria
from app.modules.categories.schemas import (
    CategoriaSalida,
    SolicitudActualizarCategoria,
    SolicitudCrearCategoria,
)

# Categorías que recibe todo hogar nuevo (después se pueden editar y ampliar).
CATEGORIAS_INICIALES = (
    "Agua", "Energía", "Gas", "Internet", "Mercado", "Arriendo",
    "Reparaciones", "Transporte", "Salud", "Préstamos", "Otros",
)


def sembrar_categorias_iniciales(db: Session, hogar_id: uuid.UUID) -> None:
    """Crea las categorías predeterminadas de un hogar recién creado."""
    repository.crear_varias(db, household_id=hogar_id, nombres=CATEGORIAS_INICIALES)


def listar_categorias(db: Session, hogar_id: uuid.UUID) -> list[CategoriaSalida]:
    """Categorías del hogar de la sesión."""
    return [CategoriaSalida.model_validate(c) for c in repository.listar(db, hogar_id)]


def crear_categoria(
    db: Session, contexto: ContextoUsuario, datos: SolicitudCrearCategoria
) -> CategoriaSalida:
    """Crea una categoría y la audita."""
    try:
        categoria = repository.crear(db, household_id=contexto.hogar_id, nombre=datos.nombre)
    except IntegrityError as exc:
        raise Conflicto("Ya existe una categoría con ese nombre en el hogar.") from exc
    auditoria.registrar(
        db,
        hogar_id=contexto.hogar_id,
        usuario_id=contexto.usuario_id,
        accion="categoria_creada",
        entidad="category",
        entidad_id=categoria.id,
        detalle={"nombre": categoria.nombre},
    )
    return CategoriaSalida.model_validate(categoria)


def actualizar_categoria(
    db: Session,
    contexto: ContextoUsuario,
    categoria_id: uuid.UUID,
    datos: SolicitudActualizarCategoria,
) -> CategoriaSalida:
    """Renombra o activa/desactiva una categoría (nunca se borra) y lo audita."""
    categoria: Categoria | None = repository.obtener(db, contexto.hogar_id, categoria_id)
    if categoria is None:
        raise NoEncontrado("La categoría no existe.")
    antes = {"nombre": categoria.nombre, "activa": categoria.activa}
    if datos.nombre is not None:
        categoria.nombre = datos.nombre
    if datos.activa is not None:
        categoria.activa = datos.activa
    try:
        db.flush()
    except IntegrityError as exc:
        raise Conflicto("Ya existe una categoría con ese nombre en el hogar.") from exc
    auditoria.registrar(
        db,
        hogar_id=contexto.hogar_id,
        usuario_id=contexto.usuario_id,
        accion="categoria_actualizada",
        entidad="category",
        entidad_id=categoria.id,
        detalle={"antes": antes, "despues": {"nombre": categoria.nombre, "activa": categoria.activa}},
    )
    return CategoriaSalida.model_validate(categoria)