# backend/app/shared/money.py
# Reglas de dinero en pesos colombianos (COP). Todo se calcula con Decimal: NUNCA con float.
# Política de redondeo: los importes son pesos enteros (sin centavos) y los repartos usan el
# método del "mayor resto", de modo que las partes SIEMPRE suman exactamente el total.

from collections.abc import Sequence
from decimal import ROUND_FLOOR, Decimal, localcontext
from typing import Annotated

from pydantic import AfterValidator, Field, PlainSerializer

UN_PESO = Decimal(1)


def validar_pesos_enteros(valor: Decimal) -> Decimal:
    """Rechaza importes con centavos y los normaliza a pesos enteros."""
    if valor != valor.to_integral_value():
        raise ValueError("Los importes en COP no llevan centavos.")
    return valor.quantize(UN_PESO)


def _serializar_pesos(valor: Decimal) -> str:
    """Los importes salen como texto de pesos enteros (nunca como número de coma flotante)."""
    return str(valor.quantize(UN_PESO))


# Tipos reutilizables en los esquemas Pydantic de entrada y salida.
PesosPositivos = Annotated[
    Decimal, Field(gt=0, max_digits=12, decimal_places=2), AfterValidator(validar_pesos_enteros)
]
PesosNoNegativos = Annotated[
    Decimal, Field(ge=0, max_digits=12, decimal_places=2), AfterValidator(validar_pesos_enteros)
]
PesosSalida = Annotated[
    Decimal, PlainSerializer(_serializar_pesos, return_type=str, when_used="json")
]


def repartir_proporcional(total: Decimal, pesos: Sequence[Decimal]) -> list[Decimal]:
    """Reparte 'total' en proporción a 'pesos' con el método del mayor resto.

    Garantías: la suma de las partes es exactamente 'total', cada parte es un peso entero y
    el resultado es determinista (ante empates en el resto gana el índice menor).
    """
    if total < 0 or total != total.to_integral_value():
        raise ValueError("El total a repartir debe ser un número entero de pesos no negativo.")
    if not pesos or any(p < 0 for p in pesos) or sum(pesos) == 0:
        raise ValueError("Los pesos del reparto deben ser no negativos y sumar más que cero.")

    with localcontext() as contexto:
        contexto.prec = 50  # precisión holgada: los cocientes no pierden información relevante
        suma_pesos = sum(pesos)
        exactos = [total * p / suma_pesos for p in pesos]
        partes = [e.to_integral_value(rounding=ROUND_FLOOR) for e in exactos]
        sobrante = int(total - sum(partes))
        # Los pesos sobrantes se entregan a quienes tienen mayor parte fraccionaria.
        orden = sorted(range(len(pesos)), key=lambda i: (-(exactos[i] - partes[i]), i))
        for i in orden[:sobrante]:
            partes[i] += 1
    return [p.quantize(UN_PESO) for p in partes]


def repartir_partes_iguales(total: Decimal, cantidad: int) -> list[Decimal]:
    """Reparte en partes iguales; los pesos que sobran van a las primeras posiciones."""
    if cantidad < 1:
        raise ValueError("Debe haber al menos una parte.")
    return repartir_proporcional(total, [Decimal(1)] * cantidad)


def formatear_cop(valor: Decimal) -> str:
    """Formato colombiano: $ 1.250.000 (punto como separador de miles, sin decimales)."""
    entero = int(valor.quantize(UN_PESO))
    texto = f"{abs(entero):,}".replace(",", ".")
    return f"-$ {texto}" if entero < 0 else f"$ {texto}"