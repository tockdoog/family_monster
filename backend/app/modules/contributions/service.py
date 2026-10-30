# backend/app/modules/contributions/service.py
# Reglas de negocio de aportes: reglas de reparto con vigencia, aportes, reembolsos y resumen.

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import Conflicto, ErrorNegocio, NoEncontrado
from app.modules.accounts import repository as repo_cuentas
from app.modules.audit import service as auditoria
from app.modules.categories import repository as repo_categorias
from app.modules.contributions import repository
from app.modules.contributions.schemas import (
    ItemReglaSalida,
    ParteSalida,
    ReglaSalida,
    ResumenAportes,
    ResumenIntegrante,
    SolicitudAporte,
    SolicitudReembolso,
    SolicitudRegla,
)
from app.modules.members import repository as repo_integrantes
from app.modules.transactions import ledger
from app.modules.transactions import repository as repo_movimientos
from app.modules.transactions.models import TipoMovimiento
from app.modules.transactions.schemas import MovimientoSalida
from app.modules.transactions.service import salida_de
from app.shared.fechas import limites_de_mes, hoy_colombia
from app.shared.idempotency import calcular_huella
from app.shared.money import formatear_cop


# ---------------------------------------------------------------------------
# Reglas de reparto
# ---------------------------------------------------------------------------
def _validar_items(solicitud: SolicitudRegla) -> None:
    """Valida que la regla sea coherente: sin repetidos, un solo método variable y porcentajes que suman 100."""
    ids = [i.integrante_id for i in solicitud.items]
    if len(set(ids)) != len(ids):
        raise ErrorNegocio("Un integrante no puede aparecer dos veces en la misma regla.")
    variables = [i for i in solicitud.items if i.tipo != "fijo"]
    if not variables:
        raise ErrorNegocio("Debe haber al menos un integrante por porcentaje o parte igual que cubra el resto del gasto.")
    if len({i.tipo for i in variables}) > 1:
        raise ErrorNegocio("No se pueden mezclar porcentajes y partes iguales en la misma regla.")
    if variables[0].tipo == "porcentaje" and sum((i.valor for i in variables), Decimal(0)) != 100:
        raise ErrorNegocio("Los porcentajes deben sumar exactamente 100.")


def _a_salida_regla(regla, items) -> ReglaSalida:
    """Convierte una regla y sus ítems en el contrato de salida."""
    return ReglaSalida(
        id=regla.id,
        nombre=regla.nombre,
        categoria_id=regla.categoria_id,
        vigente_desde=regla.vigente_desde,
        vigente_hasta=regla.vigente_hasta,
        items=[ItemReglaSalida(integrante_id=i.member_id, tipo=i.tipo, valor=i.valor) for i in items],
    )


def crear_regla(db: Session, contexto: ContextoUsuario, datos: SolicitudRegla) -> ReglaSalida:
    """Crea una regla con vigencia y cierra la anterior del mismo alcance.

    Las reglas no se editan: para cambiar un porcentaje se crea una regla nueva que rige hacia
    adelante. Los repartos ya calculados conservan su foto y no cambian.
    """
    hogar_id = contexto.hogar_id
    _validar_items(datos)

    if datos.categoria_id is not None:
        categoria = repo_categorias.obtener(db, hogar_id, datos.categoria_id)
        if categoria is None:
            raise NoEncontrado("La categoría indicada no existe en el hogar.")
    ids = {i.integrante_id for i in datos.items}
    if repo_movimientos.integrantes_existentes(db, hogar_id, ids) != ids:
        raise NoEncontrado("Alguno de los integrantes indicados no existe en el hogar.")

    # Cierra la regla vigente del mismo alcance (el día anterior al inicio de la nueva).
    abierta = repository.regla_abierta_del_alcance(db, hogar_id, datos.categoria_id)
    if abierta is not None:
        if abierta.vigente_desde >= datos.vigente_desde:
            raise ErrorNegocio("Ya existe una regla desde esa fecha o posterior para este alcance: use una fecha posterior.")
        abierta.vigente_hasta = datos.vigente_desde - timedelta(days=1)

    try:
        regla = repository.crear_regla(
            db,
            household_id=hogar_id,
            nombre=datos.nombre,
            categoria_id=datos.categoria_id,
            vigente_desde=datos.vigente_desde,
            creado_por=contexto.usuario_id,
        )
    except IntegrityError as exc:
        raise Conflicto("Ya existe una regla de ese alcance que empieza el mismo día.") from exc
    repository.crear_items(
        db,
        regla_id=regla.id,
        hogar_id=hogar_id,
        items=[(i.integrante_id, i.tipo, i.valor) for i in datos.items],
    )
    auditoria.registrar(
        db,
        hogar_id=hogar_id,
        usuario_id=contexto.usuario_id,
        accion="regla_aporte_creada",
        entidad="contribution_rule",
        entidad_id=regla.id,
        detalle={
            "nombre": regla.nombre,
            "vigente_desde": str(regla.vigente_desde),
            "categoria_id": None if regla.categoria_id is None else str(regla.categoria_id),
            "regla_anterior": None if abierta is None else str(abierta.id),
        },
    )
    return _a_salida_regla(regla, repository.items_de(db, [regla.id])[regla.id])


def listar_reglas(db: Session, hogar_id: uuid.UUID) -> list[ReglaSalida]:
    """Reglas del hogar (vigentes e históricas) con sus partes."""
    reglas = repository.listar_reglas(db, hogar_id)
    items = repository.items_de(db, [r.id for r in reglas])
    return [_a_salida_regla(r, items[r.id]) for r in reglas]


def reparto_de_movimiento(
    db: Session, hogar_id: uuid.UUID, movimiento_id: uuid.UUID
) -> list[ParteSalida]:
    """Foto del reparto que se aplicó a un gasto concreto."""
    if repo_movimientos.obtener(db, hogar_id, movimiento_id) is None:
        raise NoEncontrado("El movimiento no existe.")
    return [
        ParteSalida(integrante_id=p.member_id, regla_id=p.rule_id, tipo=p.tipo, valor=p.valor, importe=p.importe)
        for p in repository.partes_de_movimiento(db, hogar_id, movimiento_id)
    ]


# ---------------------------------------------------------------------------
# Aportes y reembolsos (movimientos reales del libro)
# ---------------------------------------------------------------------------
def _cuenta_o_404(db: Session, hogar_id: uuid.UUID, cuenta_id: uuid.UUID):
    """Cuenta del hogar de la sesión."""
    fila = repo_cuentas.obtener_con_saldo(db, hogar_id, cuenta_id)
    if fila is None:
        raise NoEncontrado("Alguna de las cuentas indicadas no existe en el hogar.")
    return fila[0]


def registrar_aporte(
    db: Session, contexto: ContextoUsuario, datos: SolicitudAporte, clave: str
) -> tuple[MovimientoSalida, bool]:
    """Registra dinero que un integrante entrega al fondo común. No es un ingreso ordinario."""
    hogar_id = contexto.hogar_id
    huella = calcular_huella("registrar_aporte", **datos.model_dump(mode="json"))
    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        return salida_de(db, previo), False

    integrante = repo_integrantes.obtener_por_id(db, hogar_id, datos.integrante_id)
    if integrante is None:
        raise NoEncontrado("El integrante indicado no existe en el hogar.")
    destino = _cuenta_o_404(db, hogar_id, datos.cuenta_destino_id)
    if destino.tipo == "personal":
        raise ErrorNegocio("El aporte debe entregarse a una cuenta del fondo común.")
    if datos.cuenta_origen_id is not None:
        origen = _cuenta_o_404(db, hogar_id, datos.cuenta_origen_id)
        if origen.tipo != "personal" or origen.propietario_id != integrante.id:
            raise ErrorNegocio("La cuenta de origen debe ser la cuenta personal del integrante que aporta.")

    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=TipoMovimiento.APORTE.value,
        importe=datos.importe,
        descripcion=(datos.descripcion or f"Aporte de {integrante.nombre}")[:500],
        fecha=datos.fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        cuenta_destino_id=datos.cuenta_destino_id,
        pagador_id=integrante.id,
    )
    return salida_de(db, movimiento), True


def _reembolso_pendiente(db: Session, hogar_id: uuid.UUID, integrante_id: uuid.UUID) -> Decimal:
    """Lo que el hogar le debe a un integrante: pagos directos menos reembolsos (histórico)."""
    pagado = repository.pagos_directos_por_integrante(db, hogar_id, None, None).get(integrante_id, Decimal(0))
    devuelto = repository.reembolsos_por_integrante(db, hogar_id, None, None).get(integrante_id, Decimal(0))
    return pagado - devuelto


def registrar_reembolso(
    db: Session, contexto: ContextoUsuario, datos: SolicitudReembolso, clave: str
) -> tuple[MovimientoSalida, bool]:
    """Devuelve dinero del fondo común a un integrante que pagó gastos del hogar con su propio dinero."""
    hogar_id = contexto.hogar_id
    huella = calcular_huella("registrar_reembolso", **datos.model_dump(mode="json"))
    previo = ledger.resolver_idempotencia(db, hogar_id, clave, huella)
    if previo is not None:
        return salida_de(db, previo), False

    # El integrante se bloquea: dos reembolsos simultáneos no pueden devolver más de lo que se le debe.
    integrante = repo_integrantes.bloquear(db, hogar_id, datos.integrante_id)
    if integrante is None:
        raise NoEncontrado("El integrante indicado no existe en el hogar.")
    origen = _cuenta_o_404(db, hogar_id, datos.cuenta_origen_id)
    destino = _cuenta_o_404(db, hogar_id, datos.cuenta_destino_id)
    if origen.tipo == "personal":
        raise ErrorNegocio("El reembolso debe salir de una cuenta del fondo común.")
    if destino.tipo != "personal" or destino.propietario_id != integrante.id:
        raise ErrorNegocio("El reembolso debe entrar a la cuenta personal del integrante.")

    pendiente = _reembolso_pendiente(db, hogar_id, integrante.id)
    if datos.importe > pendiente:
        raise ErrorNegocio(
            f"El reembolso supera lo que el hogar le debe a {integrante.nombre} ({formatear_cop(max(pendiente, Decimal(0)))})."
        )

    movimiento = ledger.registrar_asiento(
        db,
        contexto,
        tipo=TipoMovimiento.REEMBOLSO.value,
        importe=datos.importe,
        descripcion=(datos.descripcion or f"Reembolso a {integrante.nombre}")[:500],
        fecha=datos.fecha,
        clave=clave,
        huella=huella,
        cuenta_origen_id=datos.cuenta_origen_id,
        cuenta_destino_id=datos.cuenta_destino_id,
        beneficiario_id=integrante.id,
    )
    return salida_de(db, movimiento), True


# ---------------------------------------------------------------------------
# Resumen de aportes esperados y reales
# ---------------------------------------------------------------------------
def resumen_aportes(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None
) -> ResumenAportes:
    """Compara lo que cada integrante debía aportar con lo que realmente puso en el período.

    Por defecto usa el mes actual (zona horaria de Colombia). Solo cuenta movimientos confirmados.
    """
    if desde is None or hasta is None:
        hoy = hoy_colombia()
        inicio_mes, fin_mes = limites_de_mes(hoy.year, hoy.month)
        desde, hasta = desde or inicio_mes, hasta or fin_mes
    if desde > hasta:
        raise ErrorNegocio("La fecha inicial no puede ser posterior a la final.")

    esperado = repository.esperado_por_integrante(db, hogar_id, desde, hasta)
    aportes = repository.aportes_por_integrante(db, hogar_id, desde, hasta)
    directos = repository.pagos_directos_por_integrante(db, hogar_id, desde, hasta)
    reembolsos = repository.reembolsos_por_integrante(db, hogar_id, desde, hasta)
    directos_total = repository.pagos_directos_por_integrante(db, hogar_id, None, None)
    reembolsos_total = repository.reembolsos_por_integrante(db, hogar_id, None, None)

    cero = Decimal(0)
    filas: list[ResumenIntegrante] = []
    for integrante, _rol in repo_integrantes.listar_con_rol(db, hogar_id):
        i = integrante.id
        neto = aportes.get(i, cero) + directos.get(i, cero) - reembolsos.get(i, cero)
        saldo = neto - esperado.get(i, cero)
        filas.append(
            ResumenIntegrante(
                integrante_id=i,
                nombre=integrante.nombre,
                obligacion_esperada=esperado.get(i, cero),
                aportes=aportes.get(i, cero),
                pagos_directos=directos.get(i, cero),
                reembolsos=reembolsos.get(i, cero),
                aportado_neto=neto,
                saldo=saldo,
                estado="al_dia" if saldo >= 0 else "pendiente",
                reembolso_pendiente=directos_total.get(i, cero) - reembolsos_total.get(i, cero),
            )
        )
    return ResumenAportes(
        desde=desde,
        hasta=hasta,
        integrantes=filas,
        total_esperado=sum((f.obligacion_esperada for f in filas), cero),
        total_aportado_neto=sum((f.aportado_neto for f in filas), cero),
        gastos_sin_distribuir=repository.gastos_sin_distribuir(db, hogar_id, desde, hasta),
    )