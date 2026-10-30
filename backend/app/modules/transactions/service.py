# backend/app/modules/transactions/service.py
# Reglas de negocio del libro de movimientos para ingresos, gastos, transferencias y reversiones.
# Las demás operaciones con dinero (aportes, pagos, préstamos) usan el mismo libro (ledger.py).

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, ErrorNegocio, NoEncontrado
from app.modules.accounts import repository as repo_cuentas
from app.modules.audit import service as auditoria
from app.modules.contributions import distribution
from app.modules.loans import repository as repo_prestamos
from app.modules.transactions import ledger, repository
from app.modules.transactions.models import (
    EstadoMovimiento,
    LineaMovimiento,
    Movimiento,
    TipoMovimiento,
)
from app.modules.transactions.schemas import (
    LineaSalida,
    MovimientoSalida,
    SolicitudMovimiento,
    SolicitudReversion,
)
from app.shared.fechas import hoy_colombia
from app.shared.idempotency import calcular_huella
from app.shared.pagination import Pagina, ParametrosPagina


def _a_salida(movimiento: Movimiento, lineas: list[LineaMovimiento]) -> MovimientoSalida:
    """Convierte un movimiento y sus líneas en el contrato de salida."""
    # Dinero movido: lo que entra o lo que sale, el mayor de los dos. Un gasto solo tiene una línea
    # negativa y un ingreso solo una positiva; una transferencia tiene ambas y son iguales.
    entra = sum((l.importe for l in lineas if l.importe > 0), Decimal(0))
    sale = -sum((l.importe for l in lineas if l.importe < 0), Decimal(0))
    total_movido = max(entra, sale)
    return MovimientoSalida(
        id=movimiento.id,
        tipo=movimiento.tipo,
        estado=movimiento.estado,
        fecha=movimiento.fecha,
        descripcion=movimiento.descripcion,
        importe=total_movido,
        lineas=[LineaSalida(cuenta_id=l.account_id, importe=l.importe) for l in lineas],
        pagador_id=movimiento.pagador_id,
        beneficiario_id=movimiento.beneficiario_id,
        categoria_id=movimiento.categoria_id,
        registrado_por=movimiento.registrado_por,
        reversa_de_id=movimiento.reversa_de_id,
        motivo=movimiento.motivo,
        creado_en=movimiento.creado_en,
    )


def salida_de(db: Session, movimiento: Movimiento) -> MovimientoSalida:
    """Carga las líneas del movimiento y lo convierte en salida (la usan otros módulos)."""
    return _a_salida(movimiento, repository.lineas_de(db, [movimiento.id])[movimiento.id])


def _validar_combinacion(datos: SolicitudMovimiento) -> None:
    """Cada tipo de movimiento exige una combinación concreta de cuentas."""
    origen, destino = datos.cuenta_origen_id, datos.cuenta_destino_id
    if datos.tipo == TipoMovimiento.INGRESO.value and (destino is None or origen is not None):
        raise ErrorNegocio("Un ingreso requiere únicamente la cuenta de destino.")
    if datos.tipo == TipoMovimiento.GASTO.value and (origen is None or destino is not None):
        raise ErrorNegocio("Un gasto requiere únicamente la cuenta de origen.")
    if datos.tipo == TipoMovimiento.TRANSFERENCIA.value:
        if origen is None or destino is None:
            raise ErrorNegocio("Una transferencia requiere cuenta de origen y de destino.")
        if origen == destino:
            raise ErrorNegocio("La cuenta de origen y la de destino deben ser distintas.")
        if datos.categoria_id is not None:
            raise ErrorNegocio("Una transferencia no lleva categoría.")


def registrar_movimiento(
    db: Session, contexto: ContextoUsuario, datos: SolicitudMovimiento, clave: str
) -> tuple[MovimientoSalida, bool]:
    """Registra un ingreso, gasto o transferencia. Devuelve (movimiento, creado).

    Si la clave de idempotencia ya se usó con los mismos datos, devuelve el movimiento original
    (creado=False) sin crear nada nuevo. Un gasto se reparte según la regla de aporte vigente.
    """
    huella = calcular_huella("crear_movimiento", **datos.model_dump(mode="json"))
    previo = ledger.resolver_idempotencia(db, contexto.hogar_id, clave, huella)
    if previo is not None:
        return salida_de(db, previo), False

    _validar_combinacion(datos)
    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=datos.tipo,
        importe=datos.importe,
        descripcion=datos.descripcion,
        fecha=datos.fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        cuenta_destino_id=datos.cuenta_destino_id,
        pagador_id=datos.pagador_id,
        beneficiario_id=datos.beneficiario_id,
        categoria_id=datos.categoria_id,
    )
    if datos.tipo == TipoMovimiento.GASTO.value:
        distribution.distribuir_gasto(db, contexto.hogar_id, movimiento, datos.importe)
    return salida_de(db, movimiento), True


def revertir_movimiento(
    db: Session,
    contexto: ContextoUsuario,
    movimiento_id: uuid.UUID,
    datos: SolicitudReversion,
    clave: str,
) -> tuple[MovimientoSalida, bool]:
    """Contrarresta un movimiento con otro de signo opuesto, sin borrar nada del original.

    El original queda marcado como 'revertida' y la reversión guarda el motivo y quién la hizo.
    Los pagos de obligaciones y cuotas, y los repartos, dejan de contar solos porque se derivan
    únicamente de movimientos confirmados.
    """
    huella = calcular_huella(
        "revertir_movimiento", movimiento_id=str(movimiento_id), motivo=datos.motivo
    )
    hogar_id = contexto.hogar_id

    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        return salida_de(db, previo), False

    # El original se busca SOLO en el hogar de la sesión y se bloquea para evitar doble reversión.
    original = repository.obtener_bloqueando(db, hogar_id, movimiento_id)
    if original is None:
        raise NoEncontrado("El movimiento no existe.")
    if original.tipo == TipoMovimiento.REVERSION.value:
        raise ErrorNegocio("Una reversión no puede revertirse.")
    if original.estado == EstadoMovimiento.REVERTIDA.value:
        raise Conflicto("Este movimiento ya fue revertido.")
    # No se puede deshacer la entrega del dinero de un préstamo que ya tiene cuotas pagadas.
    if (
        original.tipo == TipoMovimiento.DESEMBOLSO_PRESTAMO.value
        and repo_prestamos.tiene_pagos_confirmados(db, original.id)
    ):
        raise ErrorNegocio("El préstamo ya tiene pagos: reviértalos antes de revertir el desembolso.")

    lineas_originales = repository.lineas_de(db, [original.id])[original.id]
    # Se bloquean las cuentas afectadas (en orden) para mantener los saldos consistentes.
    cuentas = repo_cuentas.bloquear_cuentas(db, hogar_id, {l.account_id for l in lineas_originales})

    # Ninguna cuenta puede quedar con saldo negativo, tampoco por una reversión: por ejemplo, no se
    # puede revertir un ingreso cuyo dinero ya se gastó. Primero hay que reponer el saldo.
    saldos_actuales = repo_cuentas.saldos_de(db, hogar_id, cuentas.keys())
    for linea in lineas_originales:
        if saldos_actuales[linea.account_id] - linea.importe < 0:
            raise ErrorNegocio(
                f"No se puede revertir: la cuenta «{cuentas[linea.account_id].nombre}» "
                "quedaría con saldo negativo."
            )

    reversion = repository.crear_movimiento(
        db,
        household_id=hogar_id,
        tipo=TipoMovimiento.REVERSION.value,
        fecha=hoy_colombia(),
        descripcion=f"Reversión: {original.descripcion}"[:500],
        registrado_por=contexto.usuario_id,
        clave_idempotencia=clave,
        huella=huella,
        reversa_de_id=original.id,
        motivo=datos.motivo,
    )
    repository.crear_lineas(
        db,
        movimiento_id=reversion.id,
        hogar_id=hogar_id,
        lineas=[(l.account_id, -l.importe) for l in lineas_originales],
    )
    # Única modificación permitida sobre el original: marcarlo como revertido.
    original.estado = EstadoMovimiento.REVERTIDA.value
    db.flush()

    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="movimiento_revertido",
        entidad="transaction",
        entidad_id=original.id,
        motivo=datos.motivo,
        detalle={"reversion_id": str(reversion.id), "tipo_original": original.tipo},
    )
    return salida_de(db, reversion), True


def listar_movimientos(
    db: Session,
    hogar_id: uuid.UUID,
    pagina: ParametrosPagina,
    *,
    tipo: str | None,
    estado: str | None,
    cuenta_id: uuid.UUID | None,
    desde: date | None,
    hasta: date | None,
) -> Pagina[MovimientoSalida]:
    """Movimientos del hogar de la sesión, filtrados y paginados."""
    movimientos, total = repository.listar(
        db, hogar_id, pagina, tipo=tipo, estado=estado, cuenta_id=cuenta_id, desde=desde, hasta=hasta
    )
    lineas = repository.lineas_de(db, [m.id for m in movimientos])
    return Pagina[MovimientoSalida](
        items=[_a_salida(m, lineas[m.id]) for m in movimientos],
        total=total,
        limite=pagina.limite,
        desplazamiento=pagina.desplazamiento,
    )