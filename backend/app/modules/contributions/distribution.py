# backend/app/modules/contributions/distribution.py
# Motor de reparto de gastos entre integrantes. El cálculo es una función pura (sin base de
# datos), por lo que se prueba de forma aislada; la persistencia guarda una "foto" del reparto.

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from sqlalchemy.orm import Session

from app.modules.contributions import repository
from app.modules.transactions.models import Movimiento
from app.shared.money import repartir_proporcional


@dataclass(frozen=True)
class ItemCalculo:
    """Parámetro de un integrante dentro de una regla."""

    integrante_id: uuid.UUID
    tipo: str  # porcentaje | parte | fijo
    valor: Decimal


@dataclass(frozen=True)
class ParteCalculada:
    """Resultado del reparto para un integrante."""

    integrante_id: uuid.UUID
    tipo: str
    valor: Decimal
    importe: Decimal


def calcular_reparto(total: Decimal, items: Sequence[ItemCalculo]) -> list[ParteCalculada]:
    """Reparte 'total' entre los integrantes de la regla; las partes suman EXACTAMENTE 'total'.

    1. Quienes tienen importe fijo pagan ese monto.
    2. Lo que queda se reparte entre los demás por porcentaje o en partes iguales
       (método del mayor resto, sin perder ni inventar pesos).
    Si los importes fijos superan el total del gasto, se escalan proporcionalmente y los demás
    pagan cero: así el reparto nunca falla ni se descuadra.
    """
    if not items:
        raise ValueError("Una regla necesita al menos un integrante.")
    # Orden estable por integrante: el resultado es siempre el mismo para los mismos datos.
    ordenados = sorted(items, key=lambda i: str(i.integrante_id))
    fijos = [i for i in ordenados if i.tipo == "fijo"]
    variables = [i for i in ordenados if i.tipo != "fijo"]
    suma_fijos = sum((i.valor for i in fijos), Decimal(0))

    importes: dict[uuid.UUID, Decimal] = {}
    if fijos and suma_fijos > total:
        for item, importe in zip(fijos, repartir_proporcional(total, [i.valor for i in fijos])):
            importes[item.integrante_id] = importe
        for item in variables:
            importes[item.integrante_id] = Decimal(0)
    else:
        for item in fijos:
            importes[item.integrante_id] = item.valor
        if variables:
            pesos = [i.valor if i.tipo == "porcentaje" else Decimal(1) for i in variables]
            for item, importe in zip(variables, repartir_proporcional(total - suma_fijos, pesos)):
                importes[item.integrante_id] = importe
        elif suma_fijos != total:
            raise ValueError("Sin integrantes variables, los importes fijos deben sumar el total.")

    return [
        ParteCalculada(i.integrante_id, i.tipo, i.valor, importes[i.integrante_id]) for i in ordenados
    ]


def distribuir_gasto(
    db: Session, hogar_id: uuid.UUID, movimiento: Movimiento, importe: Decimal
) -> int:
    """Aplica la regla vigente a un gasto y guarda la foto del reparto. Devuelve cuántas partes creó.

    Prevalece la regla de la categoría del gasto; si no hay, la regla general. Sin regla aplicable
    el gasto simplemente queda sin repartir (el resumen lo informa).
    """
    regla = None
    if movimiento.categoria_id is not None:
        regla = repository.regla_vigente(db, hogar_id, movimiento.categoria_id, movimiento.fecha)
    if regla is None:
        regla = repository.regla_vigente(db, hogar_id, None, movimiento.fecha)
    if regla is None:
        return 0

    items = repository.items_de(db, [regla.id])[regla.id]
    partes = calcular_reparto(
        importe, [ItemCalculo(i.member_id, i.tipo, i.valor) for i in items]
    )
    repository.crear_partes(
        db,
        hogar_id=hogar_id,
        movimiento_id=movimiento.id,
        regla_id=regla.id,
        partes=[(p.integrante_id, p.tipo, p.valor, p.importe) for p in partes],
    )
    return len(partes)