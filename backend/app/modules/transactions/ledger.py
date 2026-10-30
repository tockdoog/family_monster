# backend/app/modules/transactions/ledger.py
# Núcleo contable compartido: TODA operación que mueve dinero (gastos, aportes, pagos de
# obligaciones y cuotas, desembolsos, reembolsos) se registra aquí, para que las reglas de
# idempotencia, hogar, saldo, transacción y auditoría existan en un solo lugar.

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, ErrorNegocio, NoEncontrado
from app.modules.accounts import repository as repo_cuentas
from app.modules.audit import service as auditoria
from app.modules.categories import repository as repo_categorias
from app.modules.transactions import repository
from app.modules.transactions.models import Movimiento
from app.shared.fechas import hoy_colombia

MENSAJE_CLAVE_REUTILIZADA = "La clave de idempotencia ya se usó con una solicitud distinta."


def resolver_idempotencia(
    db: Session, hogar_id: uuid.UUID, clave: str, huella: str
) -> Movimiento | None:
    """Devuelve el movimiento ya creado con esa clave (repetición legítima) o None si es nueva.

    El candado serializa solicitudes duplicadas simultáneas. Si la clave existe pero con datos
    distintos, se rechaza: una clave identifica una única operación.
    """
    repository.bloquear_clave_idempotencia(db, hogar_id, clave)
    previo = repository.por_clave(db, hogar_id, clave)
    if previo is None:
        return None
    if previo.huella != huella:
        raise Conflicto(MENSAJE_CLAVE_REUTILIZADA)
    return previo


def registrar_asiento(
    db: Session,
    contexto: ContextoUsuario,
    *,
    tipo: str,
    importe: Decimal,
    descripcion: str,
    fecha: date | None,
    clave: str,
    huella: str,
    cuenta_origen_id: uuid.UUID | None = None,
    cuenta_destino_id: uuid.UUID | None = None,
    pagador_id: uuid.UUID | None = None,
    beneficiario_id: uuid.UUID | None = None,
    categoria_id: uuid.UUID | None = None,
) -> Movimiento:
    """Valida y guarda un movimiento con sus líneas y su auditoría, dentro de la transacción en curso.

    Sale dinero de la cuenta de origen (si hay) y entra en la de destino (si hay). Las validaciones
    propias de cada tipo (qué cuentas corresponden) las hace quien llama, antes de usar esta función.
    """
    hogar_id = contexto.hogar_id

    hoy = hoy_colombia()
    fecha_final = fecha or hoy
    if fecha_final > hoy:
        raise ErrorNegocio("La fecha del movimiento no puede ser futura.")

    # Las cuentas, integrantes y categoría deben existir en ESTE hogar (nunca se confía en el cliente).
    ids_cuentas = {i for i in (cuenta_origen_id, cuenta_destino_id) if i is not None}
    cuentas = repo_cuentas.bloquear_cuentas(db, hogar_id, ids_cuentas)
    if len(cuentas) != len(ids_cuentas):
        raise NoEncontrado("Alguna de las cuentas indicadas no existe en el hogar.")
    for cuenta in cuentas.values():
        if not cuenta.activa:
            raise ErrorNegocio(f"La cuenta «{cuenta.nombre}» está inactiva.")

    ids_integrantes = {i for i in (pagador_id, beneficiario_id) if i is not None}
    if repository.integrantes_existentes(db, hogar_id, ids_integrantes) != ids_integrantes:
        raise NoEncontrado("Alguno de los integrantes indicados no existe en el hogar.")

    if categoria_id is not None:
        categoria = repo_categorias.obtener(db, hogar_id, categoria_id)
        if categoria is None:
            raise NoEncontrado("La categoría indicada no existe en el hogar.")
        if not categoria.activa:
            raise ErrorNegocio(f"La categoría «{categoria.nombre}» está desactivada.")

    # Ninguna cuenta puede quedar con saldo negativo (las cuentas ya están bloqueadas).
    if cuenta_origen_id is not None:
        saldo = repo_cuentas.saldos_de(db, hogar_id, [cuenta_origen_id])[cuenta_origen_id]
        if saldo - importe < 0:
            raise ErrorNegocio(f"Saldo insuficiente en la cuenta «{cuentas[cuenta_origen_id].nombre}».")

    # Cabecera, líneas y auditoría juntas: si algo falla, todo se revierte.
    movimiento = repository.crear_movimiento(
        db,
        household_id=hogar_id,
        tipo=tipo,
        fecha=fecha_final,
        descripcion=descripcion,
        registrado_por=contexto.usuario_id,
        pagador_id=pagador_id,
        beneficiario_id=beneficiario_id,
        categoria_id=categoria_id,
        clave_idempotencia=clave,
        huella=huella,
    )
    lineas: list[tuple[uuid.UUID, Decimal]] = []
    if cuenta_origen_id is not None:
        lineas.append((cuenta_origen_id, -importe))
    if cuenta_destino_id is not None:
        lineas.append((cuenta_destino_id, importe))
    repository.crear_lineas(db, movimiento_id=movimiento.id, hogar_id=hogar_id, lineas=lineas)

    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="movimiento_registrado",
        entidad="transaction",
        entidad_id=movimiento.id,
        detalle={
            "tipo": tipo,
            "importe": str(importe),
            "cuentas": sorted(str(i) for i in ids_cuentas),
        },
    )
    return movimiento