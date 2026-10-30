# backend/app/modules/reports/service.py
# Panel principal e informes. Todo se calcula en el servidor a partir de movimientos confirmados:
# la interfaz solo muestra estos resultados, nunca recalcula cifras financieras.

import csv
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.dependencies import ContextoUsuario
from app.core.exceptions import ErrorNegocio
from app.modules.accounts import service as servicio_cuentas
from app.modules.audit import service as auditoria
from app.modules.categories import repository as repo_categorias
from app.modules.contributions import service as servicio_aportes
from app.modules.loans import repository as repo_prestamos
from app.modules.loans import service as servicio_prestamos
from app.modules.obligations import repository as repo_obligaciones
from app.modules.obligations.service import calcular_estado
from app.modules.reports import repository
from app.modules.reports.schemas import (
    GastoPorCategoria,
    InformeMensual,
    ResumenObligaciones,
    ResumenPrestamos,
    TableroSalida,
    TotalesPeriodo,
    Vencimiento,
)
from app.modules.transactions import repository as repo_movimientos
from app.modules.transactions.service import _a_salida as movimiento_a_salida
from app.shared.fechas import hoy_colombia, limites_de_mes
from app.shared.pagination import ParametrosPagina

# Máximo de movimientos que incluye un informe mensual (protege la memoria y el tiempo de respuesta).
LIMITE_MOVIMIENTOS_INFORME = 5000
SIN_CATEGORIA = "Sin categoría"


def _periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Período pedido; por defecto el mes actual en la zona horaria de Colombia."""
    if desde is None or hasta is None:
        hoy = hoy_colombia()
        inicio, fin = limites_de_mes(hoy.year, hoy.month)
        desde, hasta = desde or inicio, hasta or fin
    if desde > hasta:
        raise ErrorNegocio("La fecha inicial no puede ser posterior a la final.")
    return desde, hasta


def _totales(db: Session, hogar_id: uuid.UUID, desde: date, hasta: date) -> TotalesPeriodo:
    """Totales del período; cada concepto sale de su propio tipo de movimiento (sin contar dos veces)."""
    entradas, salidas = repository.sumas_por_tipo(db, hogar_id, desde, hasta)
    cero = Decimal(0)
    ingresos = entradas.get("ingreso", cero)
    aportes = entradas.get("aporte", cero)
    gastos = salidas.get("gasto", cero) + salidas.get("pago_obligacion", cero)
    return TotalesPeriodo(
        ingresos=ingresos,
        aportes=aportes,
        gastos=gastos,
        pagos_de_prestamos=salidas.get("pago_cuota", cero),
        balance_operativo=ingresos + aportes - gastos,
    )


def _por_categoria(db: Session, hogar_id: uuid.UUID, desde: date, hasta: date) -> list[GastoPorCategoria]:
    """Gasto del período por categoría, de mayor a menor."""
    nombres = repo_categorias.nombres_por_id(db, hogar_id)
    return [
        GastoPorCategoria(
            categoria_id=categoria_id,
            categoria=nombres.get(categoria_id, SIN_CATEGORIA) if categoria_id else SIN_CATEGORIA,
            importe=importe,
        )
        for categoria_id, importe in repository.gastos_por_categoria(db, hogar_id, desde, hasta)
    ]


def tablero(
    db: Session, hogar_id: uuid.UUID, desde: date | None, hasta: date | None, dias_vencimientos: int
) -> TableroSalida:
    """Panel principal: saldos, totales, categorías, aportes, obligaciones, préstamos y vencimientos."""
    desde, hasta = _periodo(desde, hasta)
    hoy = hoy_colombia()
    horizonte = hoy + timedelta(days=dias_vencimientos)
    cero = Decimal(0)

    cuentas = servicio_cuentas.listar_cuentas(db, hogar_id)
    aportes = servicio_aportes.resumen_aportes(db, hogar_id, desde, hasta)

    # Obligaciones: estado actual (no depende del período).
    vencimientos: list[Vencimiento] = []
    pendientes = vencidas = 0
    saldo_pendiente = saldo_vencido = cero
    for obligacion, pagado in repo_obligaciones.listar_con_pagado(db, hogar_id):
        anulada = obligacion.anulada_en is not None
        estado = calcular_estado(obligacion.importe_original, pagado, obligacion.fecha_vencimiento, anulada, hoy)
        if estado in ("pagada", "anulada"):
            continue
        saldo = obligacion.importe_original - pagado
        pendientes += 1
        saldo_pendiente += saldo
        if estado == "vencida":
            vencidas += 1
            saldo_vencido += saldo
        if obligacion.fecha_vencimiento <= horizonte:
            vencimientos.append(
                Vencimiento(
                    tipo="obligacion", referencia_id=obligacion.id, descripcion=obligacion.descripcion,
                    fecha_vencimiento=obligacion.fecha_vencimiento, saldo=saldo, vencido=estado == "vencida",
                )
            )

    # Préstamos: activos, saldo y cuotas por pagar.
    activos = cuotas_pendientes = 0
    saldo_prestamos = cero
    for prestamo in servicio_prestamos.armar_prestamos(db, repo_prestamos.listar(db, hogar_id)):
        if prestamo.estado != "activo":
            continue
        activos += 1
        saldo_prestamos += prestamo.saldo_pendiente
        for cuota in prestamo.cuotas:
            if cuota.saldo <= 0:
                continue
            cuotas_pendientes += 1
            if cuota.fecha_vencimiento <= horizonte:
                vencimientos.append(
                    Vencimiento(
                        tipo="cuota", referencia_id=cuota.id,
                        descripcion=f"Cuota {cuota.numero} de {len(prestamo.cuotas)} del préstamo ({prestamo.tipo.replace('_', ' ')})",
                        fecha_vencimiento=cuota.fecha_vencimiento, saldo=cuota.saldo, vencido=cuota.estado == "vencida",
                    )
                )

    vencimientos.sort(key=lambda v: (v.fecha_vencimiento, v.tipo, str(v.referencia_id)))
    return TableroSalida(
        desde=desde,
        hasta=hasta,
        cuentas=cuentas,
        saldo_total=sum((c.saldo_actual for c in cuentas), cero),
        totales=_totales(db, hogar_id, desde, hasta),
        gastos_por_categoria=_por_categoria(db, hogar_id, desde, hasta),
        aportes=aportes.integrantes,
        gastos_sin_distribuir=aportes.gastos_sin_distribuir,
        obligaciones=ResumenObligaciones(
            pendientes_cantidad=pendientes, saldo_pendiente_total=saldo_pendiente,
            vencidas_cantidad=vencidas, saldo_vencido=saldo_vencido,
        ),
        prestamos=ResumenPrestamos(
            activos_cantidad=activos, saldo_pendiente_total=saldo_prestamos,
            cuotas_pendientes_cantidad=cuotas_pendientes,
        ),
        proximos_vencimientos=vencimientos[:50],
    )


def informe_mensual(db: Session, hogar_id: uuid.UUID, mes: str) -> InformeMensual:
    """Informe de un mes (formato AAAA-MM) con totales, categorías y movimientos."""
    anio, numero_mes = int(mes[:4]), int(mes[5:7])
    desde, hasta = limites_de_mes(anio, numero_mes)
    movimientos, total = repo_movimientos.listar(
        db, hogar_id, ParametrosPagina(limite=LIMITE_MOVIMIENTOS_INFORME, desplazamiento=0),
        tipo=None, estado=None, cuenta_id=None, desde=desde, hasta=hasta,
    )
    lineas = repo_movimientos.lineas_de(db, [m.id for m in movimientos])
    return InformeMensual(
        mes=mes,
        desde=desde,
        hasta=hasta,
        totales=_totales(db, hogar_id, desde, hasta),
        gastos_por_categoria=_por_categoria(db, hogar_id, desde, hasta),
        total_movimientos=total,
        truncado=total > len(movimientos),
        movimientos=[movimiento_a_salida(m, lineas[m.id]) for m in movimientos],
    )


# ---------------------------------------------------------------------------
# Exportación a CSV
# ---------------------------------------------------------------------------
def _pesos(valor: Decimal) -> str:
    """Importe como pesos enteros ('500000', nunca '500000.00'): en COP no existen los centavos."""
    return str(valor.quantize(Decimal(1)))


def _texto_seguro(valor: str) -> str:
    """Neutraliza inyección de fórmulas: Excel ejecutaría celdas de texto que empiezan con = + - @."""
    return "'" + valor if valor and valor[0] in "=+-@\t\r" else valor


def informe_mensual_csv(
    db: Session, contexto: ContextoUsuario, mes: str
) -> str:
    """CSV del informe mensual (separador ';' y BOM UTF-8 para que Excel muestre bien las tildes)."""
    informe = informe_mensual(db, contexto.hogar_id, mes)
    nombres_categorias = repo_categorias.nombres_por_id(db, contexto.hogar_id)
    nombres_cuentas = {c.id: c.nombre for c in servicio_cuentas.listar_cuentas(db, contexto.hogar_id)}

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    escritor.writerow(["fecha", "tipo", "estado", "categoria", "descripcion", "importe_cop", "cuentas"])
    for m in informe.movimientos:
        cuentas = " | ".join(f"{nombres_cuentas.get(l.cuenta_id, '?')}: {_pesos(l.importe)}" for l in m.lineas)
        escritor.writerow([
            m.fecha.isoformat(),
            m.tipo,
            m.estado,
            _texto_seguro(nombres_categorias.get(m.categoria_id, "") if m.categoria_id else ""),
            _texto_seguro(m.descripcion),
            _pesos(m.importe),
            _texto_seguro(cuentas),
        ])

    # Exportar datos financieros es una acción sensible: queda registrada.
    auditoria.registrar(
        db,
        hogar_id=contexto.hogar_id,
        usuario_id=contexto.usuario_id,
        accion="informe_exportado",
        entidad="report",
        entidad_id=contexto.hogar_id,
        detalle={"mes": mes, "formato": "csv", "movimientos": len(informe.movimientos)},
    )
    return "\ufeff" + salida.getvalue()