# backend/tests/test_dinero.py
# Pruebas del módulo de dinero: precisión, redondeo del reparto y formato en COP.

import random
import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.shared.money import (
    PesosPositivos,
    formatear_cop,
    repartir_partes_iguales,
    repartir_proporcional,
    validar_pesos_enteros,
)


def test_partes_iguales_suman_exactamente_el_total():
    """100.000 entre 3 no se pierde ni se inventa un peso: 33.334 + 33.333 + 33.333."""
    partes = repartir_partes_iguales(Decimal("100000"), 3)
    assert partes == [Decimal("33334"), Decimal("33333"), Decimal("33333")]
    assert sum(partes) == Decimal("100000")


def test_porcentajes_resuelven_el_redondeo_con_mayor_resto():
    """Con 33,33 % / 33,33 % / 33,34 % el resto va a quien más lo merece y todo cuadra."""
    partes = repartir_proporcional(Decimal("100001"), [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")])
    assert sum(partes) == Decimal("100001")
    assert all(p == p.to_integral_value() for p in partes)
    assert partes[2] >= partes[0]


def test_reparto_por_porcentajes_exactos():
    """50 % / 30 % / 20 % de un importe divisible da partes exactas."""
    assert repartir_proporcional(Decimal("1000000"), [Decimal(50), Decimal(30), Decimal(20)]) == [
        Decimal("500000"), Decimal("300000"), Decimal("200000"),
    ]


def test_reparto_es_siempre_exacto_en_muchos_casos_aleatorios():
    """Propiedad: para cualquier total y pesos, las partes suman EXACTAMENTE el total."""
    azar = random.Random(2026)
    for _ in range(2000):
        cantidad = azar.randint(1, 8)
        pesos = [Decimal(azar.randint(0, 100)) for _ in range(cantidad)]
        if sum(pesos) == 0:
            continue
        total = Decimal(azar.randint(0, 50_000_000))
        partes = repartir_proporcional(total, pesos)
        assert sum(partes) == total
        assert all(p >= 0 and p == p.to_integral_value() for p in partes)
        # Quien tiene peso cero nunca recibe dinero.
        assert all(p == 0 for p, w in zip(partes, pesos) if w == 0)


def test_reparto_es_determinista():
    """El mismo reparto siempre da el mismo resultado (importante para auditar)."""
    pesos = [Decimal(1)] * 7
    assert repartir_partes_iguales(Decimal("1000003"), 7) == repartir_proporcional(Decimal("1000003"), pesos)
    assert repartir_partes_iguales(Decimal("1000003"), 7) == repartir_partes_iguales(Decimal("1000003"), 7)


@pytest.mark.parametrize(
    "total, pesos",
    [
        (Decimal("100.50"), [Decimal(1)]),      # centavos en el total
        (Decimal("-5"), [Decimal(1)]),          # total negativo
        (Decimal("100"), []),                   # sin partes
        (Decimal("100"), [Decimal(0), Decimal(0)]),  # pesos que no suman nada
        (Decimal("100"), [Decimal(-1), Decimal(2)]), # peso negativo
    ],
)
def test_reparto_rechaza_entradas_invalidas(total, pesos):
    """Entradas que no tienen sentido financiero se rechazan en lugar de producir basura."""
    with pytest.raises(ValueError):
        repartir_proporcional(total, pesos)


def test_importes_con_centavos_se_rechazan_y_los_enteros_se_aceptan():
    """COP no maneja centavos: 100.50 falla, 100.00 y 100 se normalizan a 100."""
    assert validar_pesos_enteros(Decimal("100.00")) == Decimal("100")
    with pytest.raises(ValueError):
        validar_pesos_enteros(Decimal("100.50"))
    adaptador = TypeAdapter(PesosPositivos)
    assert adaptador.validate_python("250000") == Decimal("250000")
    for invalido in ("0", "-5", "100.5", "1" + "0" * 13):
        with pytest.raises(ValidationError):
            adaptador.validate_python(invalido)


def test_formato_de_pesos_colombianos():
    """Se muestra con punto de miles, sin decimales y con signo cuando es negativo."""
    assert formatear_cop(Decimal("1250000")) == "$ 1.250.000"
    assert formatear_cop(Decimal("250000.00")) == "$ 250.000"
    assert formatear_cop(Decimal("0")) == "$ 0"
    assert formatear_cop(Decimal("-5000")) == "-$ 5.000"


def test_ningun_archivo_de_la_aplicacion_usa_float():
    """Regla 1: nunca se usa float para dinero. Esta guarda falla si alguien lo introduce."""
    raiz = Path(__file__).resolve().parent.parent / "app"
    patron = re.compile(r"\bfloat\b")
    infractores = [
        str(ruta.relative_to(raiz))
        for ruta in raiz.rglob("*.py")
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if patron.search(linea.split("#")[0])
    ]
    assert infractores == []