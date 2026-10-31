# backend/tests/modules/test_salud.py
# Pruebas de los endpoints de estado: /api/v1/salud (sin base de datos) y /api/v1/preparacion (con base de datos).

import pytest
from fastapi.testclient import TestClient


def test_salud_no_requiere_base_de_datos(cliente: TestClient) -> None:
    """El endpoint de salud responde siempre, sin consultar PostgreSQL."""
    respuesta = cliente.get("/api/v1/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


@pytest.mark.usefixtures("bd")
def test_preparacion_confirma_conexion_a_postgresql(cliente: TestClient) -> None:
    """Con la base disponible, la preparación responde 200 y confirma la conexión."""
    respuesta = cliente.get("/api/v1/preparacion")
    assert respuesta.status_code == 200
    assert respuesta.json()["base_de_datos"] == "ok"


def test_preparacion_no_filtra_detalles_cuando_la_base_falla(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si la base falla, responde 503 con un mensaje genérico y sin datos internos."""

    def fabrica_defectuosa():
        raise RuntimeError("credencial-interna-secreta")

    monkeypatch.setattr("app.main.obtener_fabrica_sesiones", fabrica_defectuosa)

    respuesta = cliente.get("/api/v1/preparacion")
    assert respuesta.status_code == 503
    assert respuesta.json()["base_de_datos"] == "error"
    assert "credencial-interna-secreta" not in respuesta.text