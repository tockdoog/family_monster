# backend/tests/test_reparto.py
# Pruebas del motor de reparto de gastos (función pura, sin base de datos).

import random
import uuid
from decimal import Decimal

import pytest

from app.modules.contributions.distribution import ItemCalculo, calcular_reparto


def _ids(n: int) -> list[uuid.UUID]:
    """Identificadores fijos y ordenables para que las pruebas sean predecibles."""
    return [uuid.UUID(int=i + 1) for i in range(n)]


def _como_dict(partes) -> dict[uuid.UUID, Decimal]:
    """Resultado como integrante -> importe."""
    return {p.integrante_id: p.importe for p in partes}


def test_porcentajes_exactos():
    """50 % / 30 % / 20 % de 1.000.000."""
    a, b, c = _ids(3)
    partes = calcular_reparto(
        Decimal("1000000"),
        [ItemCalculo(a, "porcentaje", Decimal(50)), ItemCalculo(b, "porcentaje", Decimal(30)), ItemCalculo(c, "porcentaje", Decimal(20))],
    )
    assert _como_dict(partes) == {a: Decimal(500000), b: Decimal(300000), c: Decimal(200000)}


def test_partes_iguales_resuelven_el_redondeo():
    """100.000 entre 3: 33.334 + 33.333 + 33.333, sin perder un peso."""
    a, b, c = _ids(3)
    partes = calcular_reparto(Decimal("100000"), [ItemCalculo(i, "parte", Decimal(1)) for i in (a, b, c)])
    assert sorted(_como_dict(partes).values()) == [Decimal(33333), Decimal(33333), Decimal(33334)]
    assert sum(p.importe for p in partes) == Decimal(100000)


def test_importe_fijo_mas_partes_iguales_para_el_resto():
    """Luis paga 30.000 fijos; Ana y Marta se reparten los 70.000 restantes por igual."""
    luis, ana, marta = _ids(3)
    partes = calcular_reparto(
        Decimal("100000"),
        [ItemCalculo(luis, "fijo", Decimal(30000)), ItemCalculo(ana, "parte", Decimal(1)), ItemCalculo(marta, "parte", Decimal(1))],
    )
    assert _como_dict(partes) == {luis: Decimal(30000), ana: Decimal(35000), marta: Decimal(35000)}


def test_importe_fijo_mas_porcentajes_sobre_el_resto():
    """Tras el fijo, el resto se reparte 60/40."""
    a, b, c = _ids(3)
    partes = calcular_reparto(
        Decimal("200000"),
        [ItemCalculo(a, "fijo", Decimal(50000)), ItemCalculo(b, "porcentaje", Decimal(60)), ItemCalculo(c, "porcentaje", Decimal(40))],
    )
    assert _como_dict(partes) == {a: Decimal(50000), b: Decimal(90000), c: Decimal(60000)}


def test_fijos_que_superan_el_gasto_se_escalan_y_siempre_suman_el_total():
    """Si los fijos (80.000) superan el gasto (40.000) se reducen a la mitad y los demás pagan cero."""
    a, b, c = _ids(3)
    partes = calcular_reparto(
        Decimal("40000"),
        [ItemCalculo(a, "fijo", Decimal(50000)), ItemCalculo(b, "fijo", Decimal(30000)), ItemCalculo(c, "parte", Decimal(1))],
    )
    resultado = _como_dict(partes)
    assert resultado == {a: Decimal(25000), b: Decimal(15000), c: Decimal(0)}
    assert sum(resultado.values()) == Decimal(40000)


def test_fijos_que_suman_exactamente_el_gasto_dejan_a_los_demas_en_cero():
    """Sin remanente, el resto no paga."""
    a, b = _ids(2)
    partes = calcular_reparto(Decimal("50000"), [ItemCalculo(a, "fijo", Decimal(50000)), ItemCalculo(b, "parte", Decimal(1))])
    assert _como_dict(partes) == {a: Decimal(50000), b: Decimal(0)}


def test_el_orden_de_entrada_no_cambia_el_resultado():
    """Mismos datos en distinto orden dan exactamente el mismo reparto (importa para auditar)."""
    ids = _ids(5)
    items = [ItemCalculo(i, "parte", Decimal(1)) for i in ids]
    esperado = _como_dict(calcular_reparto(Decimal("1000003"), items))
    for semilla in range(10):
        mezclados = items[:]
        random.Random(semilla).shuffle(mezclados)
        assert _como_dict(calcular_reparto(Decimal("1000003"), mezclados)) == esperado


def test_propiedad_el_reparto_siempre_suma_el_total_exacto():
    """2.000 casos aleatorios mezclando fijos, porcentajes y partes: la suma es siempre el total."""
    azar = random.Random(11)
    for _ in range(2000):
        n = azar.randint(2, 7)
        ids = _ids(n)
        total = Decimal(azar.randint(0, 20_000_000))
        n_fijos = azar.randint(0, n - 1)
        items = [ItemCalculo(ids[i], "fijo", Decimal(azar.randint(1, 5_000_000))) for i in range(n_fijos)]
        variables = ids[n_fijos:]
        if azar.random() < 0.5:
            cortes = sorted(azar.sample(range(1, 100), len(variables) - 1)) if len(variables) > 1 else []
            pesos = [b - a for a, b in zip([0] + cortes, cortes + [100])]
            items += [ItemCalculo(i, "porcentaje", Decimal(p)) for i, p in zip(variables, pesos)]
        else:
            items += [ItemCalculo(i, "parte", Decimal(1)) for i in variables]
        partes = calcular_reparto(total, items)
        assert sum(p.importe for p in partes) == total
        assert all(p.importe >= 0 and p.importe == p.importe.to_integral_value() for p in partes)


def test_entradas_invalidas():
    """Sin integrantes, o solo fijos que no suman el total, se rechaza."""
    a, b = _ids(2)
    with pytest.raises(ValueError):
        calcular_reparto(Decimal(1000), [])
    with pytest.raises(ValueError):
        calcular_reparto(Decimal(1000), [ItemCalculo(a, "fijo", Decimal(300)), ItemCalculo(b, "fijo", Decimal(300))])