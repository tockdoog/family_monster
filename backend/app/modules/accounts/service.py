# backend/app/modules/accounts/service.py
# Reglas de negocio de cuentas: creación validada, listado con saldos derivados y auditoría.

import uuid
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, ErrorNegocio, NoEncontrado
from app.modules.accounts import repository
from app.modules.accounts.models import Cuenta, TipoCuenta
from app.modules.accounts.schemas import CuentaSalida, SolicitudCrearCuenta
from app.modules.audit import service as auditoria
from app.modules.members import repository as repo_integrantes


def _a_salida(cuenta: Cuenta, saldo_actual: Decimal) -> CuentaSalida:
    """Convierte el modelo y su saldo derivado en el contrato de salida."""
    return CuentaSalida(
        id=cuenta.id,
        nombre=cuenta.nombre,
        tipo=cuenta.tipo,
        es_fondo_comun=cuenta.tipo != TipoCuenta.PERSONAL.value,
        propietario_id=cuenta.propietario_id,
        saldo_inicial=cuenta.saldo_inicial,
        saldo_actual=saldo_actual,
        activa=cuenta.activa,
    )


def listar_cuentas(db: Session, hogar_id: uuid.UUID) -> list[CuentaSalida]:
    """Cuentas del hogar con su saldo actual."""
    return [_a_salida(c, saldo) for c, saldo in repository.listar_con_saldo(db, hogar_id)]


def crear_cuenta(
    db: Session, contexto: ContextoUsuario, datos: SolicitudCrearCuenta
) -> CuentaSalida:
    """Crea una cuenta validando que el propietario (si aplica) sea del hogar, y la audita."""
    es_personal = datos.tipo == TipoCuenta.PERSONAL.value
    if es_personal and datos.propietario_id is None:
        raise ErrorNegocio("Una cuenta personal debe tener un propietario.")
    if not es_personal and datos.propietario_id is not None:
        raise ErrorNegocio("Solo las cuentas personales tienen propietario.")
    if datos.propietario_id is not None:
        # La búsqueda filtra por hogar: no se puede asignar un integrante de otro hogar.
        propietario = repo_integrantes.obtener_por_id(db, contexto.hogar_id, datos.propietario_id)
        if propietario is None:
            raise NoEncontrado("El propietario indicado no existe en el hogar.")

    try:
        cuenta = repository.crear_cuenta(
            db,
            household_id=contexto.hogar_id,
            nombre=datos.nombre,
            tipo=datos.tipo,
            saldo_inicial=datos.saldo_inicial,
            propietario_id=datos.propietario_id,
        )
    except IntegrityError as exc:
        raise Conflicto("Ya existe una cuenta con ese nombre en el hogar.") from exc

    auditoria.registrar(
        db,
        hogar_id=contexto.hogar_id,
        usuario_id=contexto.usuario_id,
        accion="cuenta_creada",
        entidad="account",
        entidad_id=cuenta.id,
        detalle={"nombre": cuenta.nombre, "tipo": cuenta.tipo, "saldo_inicial": str(cuenta.saldo_inicial)},
    )
    return _a_salida(cuenta, cuenta.saldo_inicial)