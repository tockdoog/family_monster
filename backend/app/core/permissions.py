# backend/app/core/permissions.py
# Roles y permisos del hogar. Es lógica pura (sin base de datos ni FastAPI) para poder
# probarla fácilmente. Los endpoints SIEMPRE deben llamar a exigir_permiso(): la
# interfaz de React puede ocultar botones, pero nunca decide quién puede hacer qué.

from enum import StrEnum
from types import MappingProxyType

from app.core.exceptions import Prohibido


class Rol(StrEnum):
    """Roles de un integrante dentro de un hogar (versión 1)."""

    ADMIN = "admin"
    MIEMBRO = "miembro"


class Permiso(StrEnum):
    """Acciones protegidas del sistema."""

    VER_FINANZAS = "ver_finanzas"
    REGISTRAR_MOVIMIENTOS = "registrar_movimientos"
    REVERTIR_MOVIMIENTOS = "revertir_movimientos"
    GESTIONAR_CUENTAS = "gestionar_cuentas"
    GESTIONAR_CATEGORIAS = "gestionar_categorias"
    GESTIONAR_OBLIGACIONES = "gestionar_obligaciones"
    GESTIONAR_INTEGRANTES = "gestionar_integrantes"
    GESTIONAR_REGLAS_APORTES = "gestionar_reglas_aportes"
    REGISTRAR_PAGOS = "registrar_pagos"
    GESTIONAR_PRESTAMOS = "gestionar_prestamos"
    VER_AUDITORIA = "ver_auditoria"
    EXPORTAR_INFORMES = "exportar_informes"


# Matriz de permisos por rol. Es de solo lectura para que no se altere en tiempo de ejecución.
# Versión 1: el administrador modifica todo; el miembro únicamente consulta.
PERMISOS_POR_ROL = MappingProxyType(
    {
        Rol.ADMIN: frozenset(Permiso),
        Rol.MIEMBRO: frozenset({Permiso.VER_FINANZAS}),
    }
)


def tiene_permiso(rol: Rol, permiso: Permiso) -> bool:
    """Responde si el rol dado puede ejecutar el permiso."""
    return permiso in PERMISOS_POR_ROL.get(rol, frozenset())


def exigir_permiso(rol: Rol, permiso: Permiso) -> None:
    """Lanza Prohibido (403) si el rol no tiene el permiso requerido."""
    if not tiene_permiso(rol, permiso):
        raise Prohibido()