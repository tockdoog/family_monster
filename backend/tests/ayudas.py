# backend/tests/ayudas.py
# Funciones auxiliares para las pruebas de cuentas y movimientos (no contiene pruebas).

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient


def nueva_clave() -> str:
    """Clave de idempotencia única para una operación."""
    return f"clave-{uuid.uuid4().hex}"


def crear_cuenta(cliente: TestClient, nombre: str = "Efectivo", saldo: int | str = 0, tipo: str = "efectivo", **extra) -> dict:
    """Crea una cuenta por la API y devuelve su cuerpo (verifica que sea exitoso)."""
    respuesta = cliente.post(
        "/api/v1/accounts", json={"nombre": nombre, "tipo": tipo, "saldo_inicial": saldo, **extra}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def registrar(cliente: TestClient, clave: str | None = None, **datos):
    """Registra un movimiento por la API (devuelve la respuesta sin validar el estado)."""
    return cliente.post(
        "/api/v1/transactions",
        json={"descripcion": "Movimiento de prueba", **datos},
        headers={"Idempotency-Key": clave or nueva_clave()},
    )


def registrar_ok(cliente: TestClient, **datos) -> dict:
    """Registra un movimiento y exige que se haya creado (201)."""
    respuesta = registrar(cliente, **datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def ingreso(cliente: TestClient, cuenta_id: str, importe: int | str, **extra) -> dict:
    """Atajo para registrar un ingreso."""
    return registrar_ok(cliente, tipo="ingreso", importe=importe, cuenta_destino_id=cuenta_id, **extra)


def gasto(cliente: TestClient, cuenta_id: str, importe: int | str, **extra) -> dict:
    """Atajo para registrar un gasto."""
    return registrar_ok(cliente, tipo="gasto", importe=importe, cuenta_origen_id=cuenta_id, **extra)


def transferencia(cliente: TestClient, origen: str, destino: str, importe: int | str) -> dict:
    """Atajo para registrar una transferencia."""
    return registrar_ok(
        cliente, tipo="transferencia", importe=importe, cuenta_origen_id=origen, cuenta_destino_id=destino
    )


def revertir(cliente: TestClient, movimiento_id: str, motivo: str = "Error de digitación", clave: str | None = None):
    """Revierte un movimiento (devuelve la respuesta sin validar el estado)."""
    return cliente.post(
        f"/api/v1/transactions/{movimiento_id}/reverse",
        json={"motivo": motivo},
        headers={"Idempotency-Key": clave or nueva_clave()},
    )


def saldos(cliente: TestClient) -> dict[str, Decimal]:
    """Saldo actual de cada cuenta, indexado por nombre."""
    return {c["nombre"]: Decimal(c["saldo_actual"]) for c in cliente.get("/api/v1/accounts").json()}


# ---------------------------------------------------------------------------
# Ayudas para categorías, integrantes, obligaciones y reglas de aporte
# ---------------------------------------------------------------------------
from datetime import date, timedelta  # noqa: E402

from app.shared.fechas import hoy_colombia  # noqa: E402


def categoria_id(cliente: TestClient, nombre: str) -> str:
    """Id de una categoría por su nombre."""
    return next(c["id"] for c in cliente.get("/api/v1/categories").json() if c["nombre"] == nombre)


def crear_integrante(cliente: TestClient, nombre: str) -> str:
    """Crea un integrante sin acceso a la app y devuelve su id."""
    respuesta = cliente.post("/api/v1/members", json={"nombre": nombre})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def integrantes(cliente: TestClient) -> dict[str, str]:
    """Mapa nombre -> id de los integrantes del hogar."""
    return {m["nombre"]: m["id"] for m in cliente.get("/api/v1/members").json()}


def crear_obligacion(
    cliente: TestClient, importe: int | str = 250000, categoria: str = "Agua", vence: date | None = None, **extra
):
    """Registra una obligación por la API (devuelve la respuesta sin validar el estado)."""
    cuerpo = {
        "descripcion": "Factura de prueba",
        "categoria_id": categoria_id(cliente, categoria),
        "importe_original": importe,
        "fecha_vencimiento": str(vence or hoy_colombia() + timedelta(days=15)),
        "acreedor": "Empresa de Servicios",
        **extra,
    }
    return cliente.post("/api/v1/obligations", json=cuerpo)


def obligacion_ok(cliente: TestClient, **kwargs) -> dict:
    """Registra una obligación y exige que se haya creado."""
    respuesta = crear_obligacion(cliente, **kwargs)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def pagar_obligacion(cliente: TestClient, obligacion_id: str, importe: int | str, cuenta_id: str, clave: str | None = None, **extra):
    """Paga una obligación (devuelve la respuesta sin validar el estado)."""
    return cliente.post(
        f"/api/v1/obligations/{obligacion_id}/payments",
        json={"importe": importe, "cuenta_origen_id": cuenta_id, **extra},
        headers={"Idempotency-Key": clave or nueva_clave()},
    )


def crear_regla(cliente: TestClient, items: list[dict], desde: date | None = None, categoria: str | None = None, nombre: str = "Regla de prueba"):
    """Crea una regla de reparto (devuelve la respuesta sin validar el estado)."""
    cuerpo = {
        "nombre": nombre,
        "vigente_desde": str(desde or hoy_colombia() - timedelta(days=60)),
        "items": items,
    }
    if categoria is not None:
        cuerpo["categoria_id"] = categoria_id(cliente, categoria)
    return cliente.post("/api/v1/contribution-rules", json=cuerpo)


def regla_ok(cliente: TestClient, items: list[dict], **kwargs) -> dict:
    """Crea una regla y exige que se haya creado."""
    respuesta = crear_regla(cliente, items, **kwargs)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def reparto(cliente: TestClient, movimiento_id: str) -> dict[str, Decimal]:
    """Reparto de un gasto: integrante_id -> importe."""
    filas = cliente.get(f"/api/v1/contributions/distributions/{movimiento_id}").json()
    return {f["integrante_id"]: Decimal(f["importe"]) for f in filas}