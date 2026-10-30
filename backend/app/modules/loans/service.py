# backend/app/modules/loans/service.py
# Reglas de negocio de préstamos: creación con desembolso, cuotas, pagos y estados derivados.
# Los pagos de cuotas NO son gastos ordinarios ni ingresos: tienen sus propios tipos de movimiento.

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import ErrorNegocio, NoEncontrado
from app.modules.accounts import repository as repo_cuentas
from app.modules.accounts.models import Cuenta
from app.modules.audit import service as auditoria
from app.modules.loans import repository
from app.modules.loans.models import Cuota, Prestamo
from app.modules.loans.schemas import (
    CuotaSalida,
    PagoCuotaRegistradoSalida,
    PagoCuotaSalida,
    PrestamoDetalle,
    PrestamoSalida,
    SolicitudPagoCuota,
    SolicitudPrestamo,
)
from app.modules.transactions import ledger
from app.modules.transactions import repository as repo_movimientos
from app.modules.transactions.models import EstadoMovimiento, Movimiento, TipoMovimiento
from app.shared.fechas import hoy_colombia, sumar_meses
from app.shared.idempotency import calcular_huella
from app.shared.money import formatear_cop, repartir_partes_iguales
from app.shared.pagination import Pagina, ParametrosPagina


# ---------------------------------------------------------------------------
# Estados derivados
# ---------------------------------------------------------------------------
def estado_de_cuota(importe: Decimal, pagado: Decimal, vencimiento: date, hoy: date) -> str:
    """Pagada si está saldada; vencida si pasó su fecha con saldo; parcial si hay un pago; si no, pendiente."""
    if pagado >= importe:
        return "pagada"
    if vencimiento < hoy:
        return "vencida"
    if pagado > 0:
        return "parcialmente_pagada"
    return "pendiente"


def _a_salida(
    prestamo: Prestamo,
    cuotas: list[Cuota],
    pagado_por_cuota: dict[uuid.UUID, Decimal],
    desembolso_estado: str,
    hoy: date,
) -> PrestamoSalida:
    """Arma el préstamo con sus cuotas; el estado se deriva del libro (desembolso y pagos confirmados)."""
    salidas = []
    for c in cuotas:
        pagado = pagado_por_cuota.get(c.id, Decimal(0))
        salidas.append(
            CuotaSalida(
                id=c.id,
                numero=c.numero,
                fecha_vencimiento=c.fecha_vencimiento,
                importe=c.importe,
                pagado=pagado,
                saldo=c.importe - pagado,
                estado=estado_de_cuota(c.importe, pagado, c.fecha_vencimiento, hoy),
            )
        )
    pagado_total = sum((s.pagado for s in salidas), Decimal(0))
    anulado = desembolso_estado == EstadoMovimiento.REVERTIDA.value
    if anulado:
        estado = "anulado"
    elif all(s.saldo == 0 for s in salidas):
        estado = "pagado"
    else:
        estado = "activo"
    return PrestamoSalida(
        id=prestamo.id,
        tipo=prestamo.tipo,
        prestamista_integrante_id=prestamo.prestamista_id,
        prestatario_integrante_id=prestamo.prestatario_id,
        contraparte_nombre=prestamo.contraparte_nombre,
        fecha=prestamo.fecha,
        importe=prestamo.importe,
        total_a_pagar=prestamo.total_a_pagar,
        pagado=pagado_total,
        saldo_pendiente=Decimal(0) if anulado else prestamo.total_a_pagar - pagado_total,
        estado=estado,
        condiciones=prestamo.condiciones,
        desembolso_movimiento_id=prestamo.desembolso_transaction_id,
        cuotas=salidas,
    )


def _armar(db: Session, prestamos: list[Prestamo]) -> list[PrestamoSalida]:
    """Carga cuotas, pagos y estado del desembolso de varios préstamos y los convierte en salida."""
    cuotas = repository.cuotas_de(db, [p.id for p in prestamos])
    pagado = repository.pagado_por_cuota(db, [c.id for lista in cuotas.values() for c in lista])
    estados = repository.estados_de_movimientos(db, [p.desembolso_transaction_id for p in prestamos])
    hoy = hoy_colombia()
    return [_a_salida(p, cuotas[p.id], pagado, estados[p.desembolso_transaction_id], hoy) for p in prestamos]


# Versión pública para que otros módulos (informes) obtengan los préstamos con su estado derivado.
armar_prestamos = _armar


def _obtener_o_404(db: Session, hogar_id: uuid.UUID, prestamo_id: uuid.UUID, *, bloquear: bool = False) -> Prestamo:
    """Préstamo del hogar de la sesión; los de otros hogares 'no existen'."""
    prestamo = repository.obtener(db, hogar_id, prestamo_id, bloquear=bloquear)
    if prestamo is None:
        raise NoEncontrado("El préstamo no existe.")
    return prestamo


# ---------------------------------------------------------------------------
# Validación de partes y cuentas según el tipo de préstamo
# ---------------------------------------------------------------------------
def _validar_partes(datos: SolicitudPrestamo) -> None:
    """Las partes (integrantes o tercero) deben ser coherentes con el tipo de préstamo."""
    presta, recibe, tercero = datos.prestamista_integrante_id, datos.prestatario_integrante_id, datos.contraparte_nombre
    if datos.tipo == "entre_integrantes":
        if presta is None or recibe is None or tercero is not None:
            raise ErrorNegocio("Un préstamo entre integrantes requiere prestamista y prestatario, sin tercero.")
        if presta == recibe:
            raise ErrorNegocio("El prestamista y el prestatario deben ser personas distintas.")
    elif datos.tipo == "al_hogar":
        if recibe is not None or (presta is None) == (tercero is None):
            raise ErrorNegocio("Un préstamo al hogar requiere exactamente un prestamista: un integrante o un tercero.")
    else:  # del_hogar
        if presta is not None or (recibe is None) == (tercero is None):
            raise ErrorNegocio("Un préstamo del hogar requiere exactamente un prestatario: un integrante o un tercero.")


def _cuenta_o_404(db: Session, hogar_id: uuid.UUID, cuenta_id: uuid.UUID) -> Cuenta:
    """Cuenta del hogar de la sesión."""
    fila = repo_cuentas.obtener_con_saldo(db, hogar_id, cuenta_id)
    if fila is None:
        raise NoEncontrado("Alguna de las cuentas indicadas no existe en el hogar.")
    return fila[0]


def _validar_cuentas(
    db: Session,
    hogar_id: uuid.UUID,
    tipo: str,
    *,
    sale_del_prestamista: uuid.UUID | None,
    entra_al_prestatario: uuid.UUID | None,
    prestamista_id: uuid.UUID | None,
    prestatario_id: uuid.UUID | None,
    es_pago: bool,
) -> None:
    """Verifica qué cuentas corresponden según el tipo de préstamo y si es desembolso o pago.

    En un desembolso el dinero va del prestamista al prestatario; en un pago, al revés. Aquí
    'origen' y 'destino' son los de la operación concreta que se está registrando.
    """
    origen, destino = sale_del_prestamista, entra_al_prestatario
    if tipo == "entre_integrantes":
        if origen is None or destino is None:
            raise ErrorNegocio("Un préstamo entre integrantes requiere cuenta de origen y de destino.")
        c_origen, c_destino = _cuenta_o_404(db, hogar_id, origen), _cuenta_o_404(db, hogar_id, destino)
        quien_da, quien_recibe = (prestatario_id, prestamista_id) if es_pago else (prestamista_id, prestatario_id)
        if c_origen.tipo != "personal" or c_origen.propietario_id != quien_da:
            raise ErrorNegocio("La cuenta de origen debe ser la cuenta personal de quien entrega el dinero.")
        if c_destino.tipo != "personal" or c_destino.propietario_id != quien_recibe:
            raise ErrorNegocio("La cuenta de destino debe ser la cuenta personal de quien recibe el dinero.")
        return

    # Préstamos del hogar: la contraparte está fuera del sistema; solo hay una cuenta del fondo común.
    hogar_recibe_dinero = (tipo == "al_hogar") != es_pago  # al_hogar: desembolso entra; pago sale (y al revés)
    cuenta_hogar, cuenta_prohibida = (destino, origen) if hogar_recibe_dinero else (origen, destino)
    if cuenta_hogar is None:
        raise ErrorNegocio(
            "Indique la cuenta del fondo común que "
            + ("recibe" if hogar_recibe_dinero else "entrega")
            + " el dinero."
        )
    if cuenta_prohibida is not None:
        raise ErrorNegocio("En un préstamo del hogar solo se indica la cuenta del fondo común.")
    if _cuenta_o_404(db, hogar_id, cuenta_hogar).tipo == "personal":
        raise ErrorNegocio("La cuenta debe ser del fondo común, no una cuenta personal.")


# ---------------------------------------------------------------------------
# Operaciones
# ---------------------------------------------------------------------------
def crear_prestamo(
    db: Session, contexto: ContextoUsuario, datos: SolicitudPrestamo, clave: str
) -> tuple[PrestamoSalida, bool]:
    """Crea el préstamo, sus cuotas y su desembolso en una sola transacción. Devuelve (préstamo, creado)."""
    hogar_id = contexto.hogar_id
    huella = calcular_huella("crear_prestamo", **datos.model_dump(mode="json"))
    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        return _armar(db, [repository.prestamo_por_desembolso(db, previo.id)])[0], False

    _validar_partes(datos)
    total = datos.total_a_pagar or datos.importe
    if total < datos.importe:
        raise ErrorNegocio("El total a pagar no puede ser menor que el importe prestado.")
    ids = {i for i in (datos.prestamista_integrante_id, datos.prestatario_integrante_id) if i is not None}
    if repo_movimientos.integrantes_existentes(db, hogar_id, ids) != ids:
        raise NoEncontrado("Alguno de los integrantes indicados no existe en el hogar.")
    _validar_cuentas(
        db, hogar_id, datos.tipo,
        sale_del_prestamista=datos.cuenta_origen_id, entra_al_prestatario=datos.cuenta_destino_id,
        prestamista_id=datos.prestamista_integrante_id, prestatario_id=datos.prestatario_integrante_id,
        es_pago=False,
    )

    fecha = datos.fecha or hoy_colombia()
    primer_vencimiento = datos.primer_vencimiento or sumar_meses(fecha, 1)
    if primer_vencimiento < fecha:
        raise ErrorNegocio("El primer vencimiento no puede ser anterior a la fecha del préstamo.")

    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=TipoMovimiento.DESEMBOLSO_PRESTAMO.value,
        importe=datos.importe,
        descripcion="Desembolso de préstamo",
        fecha=fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        cuenta_destino_id=datos.cuenta_destino_id,
        pagador_id=datos.prestamista_integrante_id,
        beneficiario_id=datos.prestatario_integrante_id,
    )
    prestamo = repository.crear_prestamo(
        db,
        household_id=hogar_id,
        tipo=datos.tipo,
        prestamista_id=datos.prestamista_integrante_id,
        prestatario_id=datos.prestatario_integrante_id,
        contraparte_nombre=datos.contraparte_nombre,
        importe=datos.importe,
        total_a_pagar=total,
        fecha=fecha,
        numero_cuotas=datos.numero_cuotas,
        condiciones=datos.condiciones,
        desembolso_transaction_id=movimiento.id,
        creado_por=contexto.usuario_id,
    )
    # Cuotas iguales que suman exactamente el total (los pesos sobrantes van a las primeras).
    importes = repartir_partes_iguales(total, datos.numero_cuotas)
    repository.crear_cuotas(
        db,
        prestamo_id=prestamo.id,
        hogar_id=hogar_id,
        cuotas=[(n + 1, sumar_meses(primer_vencimiento, n), importes[n]) for n in range(datos.numero_cuotas)],
    )
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="prestamo_creado",
        entidad="loan",
        entidad_id=prestamo.id,
        detalle={
            "tipo": datos.tipo,
            "importe": str(datos.importe),
            "total_a_pagar": str(total),
            "cuotas": datos.numero_cuotas,
            "desembolso_movimiento_id": str(movimiento.id),
        },
    )
    return _armar(db, [prestamo])[0], True


def listar_prestamos(
    db: Session, hogar_id: uuid.UUID, pagina: ParametrosPagina, estado: str | None
) -> Pagina[PrestamoSalida]:
    """Préstamos del hogar con filtro opcional por estado derivado y paginación."""
    salidas = _armar(db, repository.listar(db, hogar_id))
    if estado is not None:
        salidas = [s for s in salidas if s.estado == estado]
    corte = salidas[pagina.desplazamiento : pagina.desplazamiento + pagina.limite]
    return Pagina[PrestamoSalida](
        items=corte, total=len(salidas), limite=pagina.limite, desplazamiento=pagina.desplazamiento
    )


def obtener_prestamo(db: Session, hogar_id: uuid.UUID, prestamo_id: uuid.UUID) -> PrestamoDetalle:
    """Detalle de un préstamo con cuotas e historial de pagos."""
    prestamo = _obtener_o_404(db, hogar_id, prestamo_id)
    base = _armar(db, [prestamo])[0]
    pagos = [
        PagoCuotaSalida(movimiento_id=m.id, cuota_numero=n, fecha=m.fecha, importe=p.importe, estado_movimiento=m.estado)
        for p, n, m in repository.pagos_de_prestamo(db, prestamo.id)
    ]
    return PrestamoDetalle(**base.model_dump(), pagos=pagos)


def _pago_salida(movimiento: Movimiento, numero: int, importe: Decimal) -> PagoCuotaSalida:
    """Contrato de salida de un pago de cuota."""
    return PagoCuotaSalida(
        movimiento_id=movimiento.id, cuota_numero=numero, fecha=movimiento.fecha,
        importe=importe, estado_movimiento=movimiento.estado,
    )


def pagar_cuota(
    db: Session,
    contexto: ContextoUsuario,
    prestamo_id: uuid.UUID,
    datos: SolicitudPagoCuota,
    clave: str,
) -> tuple[PagoCuotaRegistradoSalida, bool]:
    """Paga (total o parcialmente) una cuota. Crea un movimiento 'pago_cuota', no un gasto ni un ingreso."""
    hogar_id = contexto.hogar_id
    huella = calcular_huella("pagar_cuota", prestamo_id=str(prestamo_id), **datos.model_dump(mode="json"))
    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        pago, cuota = repository.pago_por_movimiento(db, previo.id)
        prestamo = _obtener_o_404(db, hogar_id, cuota.loan_id)
        return PagoCuotaRegistradoSalida(
            pago=_pago_salida(previo, cuota.numero, pago.importe), prestamo=_armar(db, [prestamo])[0]
        ), False

    # El préstamo se bloquea: dos pagos simultáneos no pueden sumar más que el saldo de la cuota.
    prestamo = _obtener_o_404(db, hogar_id, prestamo_id, bloquear=True)
    actual = _armar(db, [prestamo])[0]
    if actual.estado == "anulado":
        raise ErrorNegocio("El préstamo está anulado y no admite pagos.")
    cuota_actual = next((c for c in actual.cuotas if c.numero == datos.cuota_numero), None)
    if cuota_actual is None:
        raise NoEncontrado("La cuota indicada no existe en este préstamo.")
    if datos.importe > cuota_actual.saldo:
        raise ErrorNegocio(f"El pago supera el saldo de la cuota ({formatear_cop(cuota_actual.saldo)}).")

    # En un pago el dinero va del prestatario al prestamista (al revés que en el desembolso).
    _validar_cuentas(
        db, hogar_id, prestamo.tipo,
        sale_del_prestamista=datos.cuenta_origen_id, entra_al_prestatario=datos.cuenta_destino_id,
        prestamista_id=prestamo.prestamista_id, prestatario_id=prestamo.prestatario_id,
        es_pago=True,
    )
    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=TipoMovimiento.PAGO_CUOTA.value,
        importe=datos.importe,
        descripcion=f"Pago de la cuota {datos.cuota_numero} de {prestamo.numero_cuotas}",
        fecha=datos.fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        cuenta_destino_id=datos.cuenta_destino_id,
        pagador_id=prestamo.prestatario_id,
        beneficiario_id=prestamo.prestamista_id,
    )
    cuota = next(c for c in repository.cuotas_de(db, [prestamo.id])[prestamo.id] if c.numero == datos.cuota_numero)
    repository.crear_pago(db, hogar_id=hogar_id, cuota_id=cuota.id, movimiento_id=movimiento.id, importe=datos.importe)
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="cuota_pagada",
        entidad="loan",
        entidad_id=prestamo.id,
        detalle={"cuota": datos.cuota_numero, "importe": str(datos.importe), "movimiento_id": str(movimiento.id)},
    )
    return PagoCuotaRegistradoSalida(
        pago=_pago_salida(movimiento, datos.cuota_numero, datos.importe), prestamo=_armar(db, [prestamo])[0]
    ), True