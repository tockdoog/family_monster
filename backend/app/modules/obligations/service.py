# backend/app/modules/obligations/service.py
# Reglas de negocio de obligaciones: alta, pagos parciales, anulación y estado derivado.

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, ErrorNegocio, NoEncontrado
from app.modules.audit import service as auditoria
from app.modules.categories import repository as repo_categorias
from app.modules.contributions import distribution
from app.modules.obligations import repository
from app.modules.obligations.models import Obligacion
from app.modules.obligations.schemas import (
    ObligacionDetalle,
    ObligacionSalida,
    PagoObligacionSalida,
    PagoRegistradoSalida,
    SolicitudAnularObligacion,
    SolicitudCrearObligacion,
    SolicitudPagoObligacion,
)
from app.modules.transactions import ledger
from app.modules.transactions import repository as repo_movimientos
from app.modules.transactions.models import TipoMovimiento
from app.shared.fechas import hoy_colombia
from app.shared.idempotency import calcular_huella
from app.shared.money import formatear_cop
from app.shared.pagination import Pagina, ParametrosPagina


def calcular_estado(
    importe: Decimal, pagado: Decimal, vencimiento: date, anulada: bool, hoy: date
) -> str:
    """Estado según importes y fechas. Prioridad: anulada > pagada > vencida > parcial > pendiente."""
    if anulada:
        return "anulada"
    if pagado >= importe:
        return "pagada"
    if vencimiento < hoy:
        return "vencida"
    if pagado > 0:
        return "parcialmente_pagada"
    return "pendiente"


def _a_salida(obligacion: Obligacion, pagado: Decimal, hoy: date) -> ObligacionSalida:
    """Convierte la obligación y lo pagado en el contrato de salida."""
    anulada = obligacion.anulada_en is not None
    return ObligacionSalida(
        id=obligacion.id,
        descripcion=obligacion.descripcion,
        categoria_id=obligacion.categoria_id,
        importe_original=obligacion.importe_original,
        pagado=pagado,
        # Una obligación anulada ya no se debe: su saldo pendiente es cero.
        saldo_pendiente=Decimal(0) if anulada else obligacion.importe_original - pagado,
        estado=calcular_estado(obligacion.importe_original, pagado, obligacion.fecha_vencimiento, anulada, hoy),
        fecha_creacion=obligacion.fecha_creacion,
        fecha_vencimiento=obligacion.fecha_vencimiento,
        acreedor=obligacion.acreedor,
        responsable_id=obligacion.responsable_id,
        motivo_anulacion=obligacion.motivo_anulacion,
    )


def _obtener_o_404(db: Session, hogar_id: uuid.UUID, obligacion_id: uuid.UUID, *, bloquear: bool = False) -> Obligacion:
    """Obligación del hogar de la sesión; las de otros hogares 'no existen'."""
    obligacion = repository.obtener(db, hogar_id, obligacion_id, bloquear=bloquear)
    if obligacion is None:
        raise NoEncontrado("La obligación no existe.")
    return obligacion


def crear_obligacion(
    db: Session, contexto: ContextoUsuario, datos: SolicitudCrearObligacion
) -> ObligacionSalida:
    """Registra una obligación validando categoría, responsable y fechas, y la audita."""
    hogar_id = contexto.hogar_id
    categoria = repo_categorias.obtener(db, hogar_id, datos.categoria_id)
    if categoria is None:
        raise NoEncontrado("La categoría indicada no existe en el hogar.")
    if not categoria.activa:
        raise ErrorNegocio(f"La categoría «{categoria.nombre}» está desactivada.")
    if datos.responsable_id is not None and datos.responsable_id not in repo_movimientos.integrantes_existentes(
        db, hogar_id, [datos.responsable_id]
    ):
        raise NoEncontrado("El responsable indicado no existe en el hogar.")

    hoy = hoy_colombia()
    fecha_creacion = datos.fecha_creacion or hoy
    if fecha_creacion > hoy:
        raise ErrorNegocio("La fecha de creación no puede ser futura.")
    if datos.fecha_vencimiento < fecha_creacion:
        raise ErrorNegocio("El vencimiento no puede ser anterior a la fecha de creación.")

    obligacion = repository.crear(
        db,
        household_id=hogar_id,
        descripcion=datos.descripcion,
        categoria_id=datos.categoria_id,
        importe_original=datos.importe_original,
        fecha_creacion=fecha_creacion,
        fecha_vencimiento=datos.fecha_vencimiento,
        acreedor=datos.acreedor,
        responsable_id=datos.responsable_id,
    )
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="obligacion_creada",
        entidad="obligation",
        entidad_id=obligacion.id,
        detalle={"importe": str(obligacion.importe_original), "acreedor": obligacion.acreedor},
    )
    return _a_salida(obligacion, Decimal(0), hoy)


def listar_obligaciones(
    db: Session, hogar_id: uuid.UUID, pagina: ParametrosPagina, estado: str | None
) -> Pagina[ObligacionSalida]:
    """Obligaciones del hogar, con filtro opcional por estado derivado y paginación.

    El volumen de un hogar es pequeño, por eso el estado se calcula en un único lugar (Python)
    y se filtra después: así no existen dos lógicas de estado que puedan contradecirse.
    """
    hoy = hoy_colombia()
    salidas = [_a_salida(o, pagado, hoy) for o, pagado in repository.listar_con_pagado(db, hogar_id)]
    if estado is not None:
        salidas = [s for s in salidas if s.estado == estado]
    corte = salidas[pagina.desplazamiento : pagina.desplazamiento + pagina.limite]
    return Pagina[ObligacionSalida](
        items=corte, total=len(salidas), limite=pagina.limite, desplazamiento=pagina.desplazamiento
    )


def _pagos_salida(db: Session, obligacion_id: uuid.UUID) -> list[PagoObligacionSalida]:
    """Historial de pagos de la obligación (incluye los revertidos, marcados por su estado)."""
    return [
        PagoObligacionSalida(
            movimiento_id=m.id, fecha=m.fecha, importe=pago.importe, estado_movimiento=m.estado
        )
        for pago, m in repository.pagos_de(db, obligacion_id)
    ]


def obtener_obligacion(db: Session, hogar_id: uuid.UUID, obligacion_id: uuid.UUID) -> ObligacionDetalle:
    """Detalle de una obligación con su historial de pagos."""
    obligacion = _obtener_o_404(db, hogar_id, obligacion_id)
    base = _a_salida(obligacion, repository.pagado_de(db, obligacion.id), hoy_colombia())
    return ObligacionDetalle(**base.model_dump(), pagos=_pagos_salida(db, obligacion.id))


def pagar_obligacion(
    db: Session,
    contexto: ContextoUsuario,
    obligacion_id: uuid.UUID,
    datos: SolicitudPagoObligacion,
    clave: str,
) -> tuple[PagoRegistradoSalida, bool]:
    """Paga (total o parcialmente) una obligación. Devuelve (resultado, creado).

    Crea un movimiento real 'pago_obligacion' que sale de la cuenta indicada, lo vincula a la
    obligación y reparte el gasto entre los integrantes según la regla de aporte vigente.
    """
    hogar_id = contexto.hogar_id
    huella = calcular_huella("pagar_obligacion", obligacion_id=str(obligacion_id), **datos.model_dump(mode="json"))

    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        pago = repository.pago_por_movimiento(db, previo.id)
        obligacion = _obtener_o_404(db, hogar_id, pago.obligation_id)
        return _resultado_pago(db, obligacion, previo, pago.importe), False

    # La obligación se bloquea: dos pagos simultáneos no pueden sumar más que el saldo.
    obligacion = _obtener_o_404(db, hogar_id, obligacion_id, bloquear=True)
    if obligacion.anulada_en is not None:
        raise ErrorNegocio("La obligación está anulada y no admite pagos.")
    saldo = obligacion.importe_original - repository.pagado_de(db, obligacion.id)
    if datos.importe > saldo:
        raise ErrorNegocio(f"El pago supera el saldo pendiente de la obligación ({formatear_cop(saldo)}).")

    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=TipoMovimiento.PAGO_OBLIGACION.value,
        importe=datos.importe,
        descripcion=(datos.descripcion or f"Pago: {obligacion.descripcion}")[:500],
        fecha=datos.fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        categoria_id=obligacion.categoria_id,
    )
    repository.crear_pago(
        db, hogar_id=hogar_id, obligacion_id=obligacion.id, movimiento_id=movimiento.id, importe=datos.importe
    )
    distribution.distribuir_gasto(db, hogar_id, movimiento, datos.importe)
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="obligacion_pagada",
        entidad="obligation",
        entidad_id=obligacion.id,
        detalle={"movimiento_id": str(movimiento.id), "importe": str(datos.importe)},
    )
    return _resultado_pago(db, obligacion, movimiento, datos.importe), True


def _resultado_pago(db: Session, obligacion: Obligacion, movimiento, importe: Decimal) -> PagoRegistradoSalida:
    """Arma la respuesta de un pago con la obligación ya actualizada."""
    return PagoRegistradoSalida(
        pago=PagoObligacionSalida(
            movimiento_id=movimiento.id, fecha=movimiento.fecha, importe=importe, estado_movimiento=movimiento.estado
        ),
        obligacion=_a_salida(obligacion, repository.pagado_de(db, obligacion.id), hoy_colombia()),
    )


def anular_obligacion(
    db: Session, contexto: ContextoUsuario, obligacion_id: uuid.UUID, datos: SolicitudAnularObligacion
) -> ObligacionSalida:
    """Anula una obligación sin pagos confirmados (nunca se borra) y deja constancia del motivo."""
    obligacion = _obtener_o_404(db, contexto.hogar_id, obligacion_id, bloquear=True)
    if obligacion.anulada_en is not None:
        raise Conflicto("La obligación ya está anulada.")
    pagado = repository.pagado_de(db, obligacion.id)
    if pagado > 0:
        raise ErrorNegocio("La obligación tiene pagos: revierta primero esos pagos para poder anularla.")

    obligacion.anulada_en = datetime.now(timezone.utc)
    obligacion.motivo_anulacion = datos.motivo
    obligacion.anulada_por = contexto.usuario_id
    db.flush()
    auditoria.registrar(
        db,
        hogar_id=contexto.hogar_id,
        usuario_id=contexto.usuario_id,
        accion="obligacion_anulada",
        entidad="obligation",
        entidad_id=obligacion.id,
        motivo=datos.motivo,
    )
    return _a_salida(obligacion, pagado, hoy_colombia())