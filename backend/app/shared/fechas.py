# backend/app/shared/fechas.py
# Fechas de negocio en la zona horaria de Colombia. La base guarda instantes en UTC;
# las fechas contables ("hoy", vencimientos) se interpretan siempre en America/Bogota.

import calendar
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


def hoy_colombia() -> date:
    """Fecha actual en Colombia (no en UTC): a las 8 p. m. en Bogotá ya es 'mañana' en UTC."""
    return datetime.now(timezone.utc).astimezone(ZONA_COLOMBIA).date()


def sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses calendario; si el día no existe en el mes destino usa el último día (31 ene + 1 mes = 28 feb)."""
    indice = fecha.month - 1 + meses
    anio = fecha.year + indice // 12
    mes = indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def limites_de_mes(anio: int, mes: int) -> tuple[date, date]:
    """Primer y último día de un mes."""
    return date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])