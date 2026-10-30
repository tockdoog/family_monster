# backend/app/shared/pagination.py
# Paginación estándar de todos los listados: límite acotado y respuesta con el total.

from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

T = TypeVar("T")


@dataclass(frozen=True)
class ParametrosPagina:
    """Parámetros de página validados (el límite máximo protege el rendimiento)."""

    limite: int
    desplazamiento: int


def _obtener_pagina(
    limite: Annotated[int, Query(ge=1, le=100)] = 50,
    desplazamiento: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> ParametrosPagina:
    """Lee y valida ?limite= y ?desplazamiento= de la URL."""
    return ParametrosPagina(limite=limite, desplazamiento=desplazamiento)


# Alias para inyectar en los endpoints.
Paginacion = Annotated[ParametrosPagina, Depends(_obtener_pagina)]


class Pagina(BaseModel, Generic[T]):
    """Respuesta paginada: elementos de la página y total de resultados."""

    items: list[T]
    total: int
    limite: int
    desplazamiento: int