# backend/tests/modules/test_informes.py
# Pruebas del panel principal y de los informes: coherencia con el libro, períodos, CSV y permisos.

import csv
import io
from datetime import timedelta
from decimal import Decimal

import pytest

from app.shared.fechas import hoy_colombia
from tests.ayudas import (
    categoria_id,
    crear_cuenta,
    crear_integrante,
    crear_obligacion,
    gasto,
    ingreso,
    integrantes,
    nueva_clave,
    obligacion_ok,
    pagar_obligacion,
    registrar_ok,
    revertir,
    transferencia,
)

TABLERO = "/api/v1/dashboard/summary"
MENSUAL = "/api/v1/reports/monthly"
ADMIN = "ana@example.com"


def _mes_actual() -> str:
    """Mes en curso en formato AAAA-MM (zona horaria de Colombia)."""
    return hoy_colombia().strftime("%Y-%m")


@pytest.fixture
def escenario(crear_hogar, nuevo_cliente, iniciar_sesion):
    """Hogar con movimientos de todos los tipos para comprobar que cada cifra se cuenta una sola vez."""
    hogar = crear_hogar()
    admin = iniciar_sesion(nuevo_cliente(), ADMIN)
    crear_integrante(admin, "Luis")
    ids = integrantes(admin)
    hoy = hoy_colombia()

    banco = crear_cuenta(admin, "Banco", saldo=1000000, tipo="banco")
    efectivo = crear_cuenta(admin, "Efectivo")

    ingreso(admin, banco["id"], 500000, categoria_id=categoria_id(admin, "Otros"))
    registrar_ok(admin, tipo="aporte" if False else "ingreso", importe=1, cuenta_destino_id=efectivo["id"])  # ingreso mínimo
    admin.post(
        "/api/v1/contributions",
        json={"integrante_id": ids["Luis"], "importe": 200000, "cuenta_destino_id": banco["id"]},
        headers={"Idempotency-Key": nueva_clave()},
    )
    gasto(admin, banco["id"], 100000, categoria_id=categoria_id(admin, "Mercado"))
    gasto(admin, banco["id"], 50000, categoria_id=categoria_id(admin, "Agua"))
    errado = gasto(admin, banco["id"], 30000, categoria_id=categoria_id(admin, "Mercado"))
    revertir(admin, errado["id"], "Gasto registrado por error")  # no debe contar en ningún total
    transferencia(admin, banco["id"], efectivo["id"], 300000)    # no debe contar como ingreso ni gasto

    pagada = obligacion_ok(admin, importe=80000, categoria="Energía")
    pagar_obligacion(admin, pagada["id"], 80000, banco["id"])

    prestamo = admin.post(
        "/api/v1/loans",
        json={"tipo": "al_hogar", "contraparte_nombre": "Banco Ejemplo", "importe": 600000, "numero_cuotas": 2,
              "primer_vencimiento": str(hoy + timedelta(days=7)), "cuenta_destino_id": banco["id"]},
        headers={"Idempotency-Key": nueva_clave()},
    ).json()
    admin.post(
        f"/api/v1/loans/{prestamo['id']}/payments",
        json={"cuota_numero": 1, "importe": 300000, "cuenta_origen_id": banco["id"]},
        headers={"Idempotency-Key": nueva_clave()},
    )
    return {"admin": admin, "hogar": hogar, "ids": ids, "banco": banco, "efectivo": efectivo, "prestamo": prestamo}


def test_los_totales_del_panel_cuentan_cada_concepto_una_sola_vez(escenario):
    """Ingresos, aportes, gastos y cuotas salen de sus propios tipos; transferencias, reversiones y préstamos no se mezclan."""
    t = escenario["admin"].get(TABLERO).json()["totales"]
    assert t["ingresos"] == "500001"
    assert t["aportes"] == "200000"
    assert t["gastos"] == "230000"           # 100.000 + 50.000 + 80.000 (el gasto revertido no cuenta)
    assert t["pagos_de_prestamos"] == "300000"
    assert t["balance_operativo"] == str(500001 + 200000 - 230000)


def test_el_panel_coincide_con_un_calculo_independiente_sobre_los_movimientos(escenario):
    """Regla 20: los totales e informes coinciden con lo que se obtiene sumando los movimientos confirmados."""
    admin = escenario["admin"]
    todos = []
    for pagina in range(0, 400, 100):
        cuerpo = admin.get("/api/v1/transactions", params={"limite": 100, "desplazamiento": pagina}).json()
        todos += cuerpo["items"]
        if len(todos) >= cuerpo["total"]:
            break
    confirmados = [m for m in todos if m["estado"] == "confirmada"]

    def entradas(tipo):
        return sum((Decimal(l["importe"]) for m in confirmados if m["tipo"] == tipo for l in m["lineas"] if Decimal(l["importe"]) > 0), Decimal(0))

    def salidas(*tipos):
        return sum((-Decimal(l["importe"]) for m in confirmados if m["tipo"] in tipos for l in m["lineas"] if Decimal(l["importe"]) < 0), Decimal(0))

    tablero = admin.get(TABLERO).json()
    t = tablero["totales"]
    assert Decimal(t["ingresos"]) == entradas("ingreso")
    assert Decimal(t["aportes"]) == entradas("aporte")
    assert Decimal(t["gastos"]) == salidas("gasto", "pago_obligacion")
    assert Decimal(t["pagos_de_prestamos"]) == salidas("pago_cuota")
    # Los gastos por categoría suman exactamente el total de gastos.
    assert sum(Decimal(c["importe"]) for c in tablero["gastos_por_categoria"]) == Decimal(t["gastos"])
    # El saldo total del hogar es la suma de todos sus movimientos sobre los saldos iniciales.
    todas_las_lineas = sum((Decimal(l["importe"]) for m in todos for l in m["lineas"]), Decimal(0))
    assert Decimal(tablero["saldo_total"]) == Decimal(1000000) + todas_las_lineas
    assert Decimal(tablero["saldo_total"]) == Decimal(1770001)


def test_gastos_por_categoria_ordenados_de_mayor_a_menor(escenario):
    """El desglose usa los nombres de las categorías y va de mayor a menor."""
    filas = escenario["admin"].get(TABLERO).json()["gastos_por_categoria"]
    assert [(f["categoria"], f["importe"]) for f in filas] == [("Mercado", "100000"), ("Energía", "80000"), ("Agua", "50000")]


def test_saldos_por_cuenta_y_sin_dinero_creado_ni_perdido(escenario):
    """El panel muestra cada cuenta con su saldo derivado."""
    saldos = {c["nombre"]: c["saldo_actual"] for c in escenario["admin"].get(TABLERO).json()["cuentas"]}
    assert saldos["Efectivo"] == "300001"
    assert saldos["Banco"] == "1470000"  # 1.000.000 + 500.000 + 200.000 - 150.000 - 80.000 - 300.000 + 600.000 - 300.000


def test_obligaciones_prestamos_y_vencimientos(escenario):
    """Cuenta pendientes y vencidas, y lista los próximos vencimientos de obligaciones y cuotas."""
    admin, hoy = escenario["admin"], hoy_colombia()
    obligacion_ok(admin, importe=120000, vence=hoy + timedelta(days=10))
    obligacion_ok(admin, importe=40000, vence=hoy - timedelta(days=2), fecha_creacion=str(hoy - timedelta(days=20)))
    cuerpo = admin.get(TABLERO).json()
    assert cuerpo["obligaciones"] == {
        "pendientes_cantidad": 2, "saldo_pendiente_total": "160000", "vencidas_cantidad": 1, "saldo_vencido": "40000",
    }
    assert cuerpo["prestamos"] == {"activos_cantidad": 1, "saldo_pendiente_total": "300000", "cuotas_pendientes_cantidad": 1}

    # La cuota 1 ya está pagada: queda la cuota 2, que vence más de 30 días después.
    proximos = [(v["tipo"], v["saldo"], v["vencido"]) for v in cuerpo["proximos_vencimientos"]]
    assert proximos == [("obligacion", "40000", True), ("obligacion", "120000", False)]
    ampliado = admin.get(TABLERO, params={"dias_vencimientos": 60}).json()["proximos_vencimientos"]
    assert [(v["tipo"], v["saldo"]) for v in ampliado] == [("obligacion", "40000"), ("obligacion", "120000"), ("cuota", "300000")]
    corto = admin.get(TABLERO, params={"dias_vencimientos": 5}).json()["proximos_vencimientos"]
    assert [v["saldo"] for v in corto] == ["40000"]
    assert admin.get(TABLERO, params={"dias_vencimientos": 0}).status_code == 422


def test_periodo_por_defecto_es_el_mes_actual_y_se_puede_cambiar(escenario):
    """Un ingreso de hace 100 días no cuenta en el mes actual, pero sí al ampliar el período."""
    admin, hoy = escenario["admin"], hoy_colombia()
    registrar_ok(admin, tipo="ingreso", importe=70000, cuenta_destino_id=escenario["banco"]["id"], fecha=str(hoy - timedelta(days=100)))
    assert admin.get(TABLERO).json()["totales"]["ingresos"] == "500001"
    amplio = admin.get(TABLERO, params={"desde": str(hoy - timedelta(days=120)), "hasta": str(hoy)}).json()
    assert amplio["totales"]["ingresos"] == "570001"
    assert admin.get(TABLERO, params={"desde": str(hoy), "hasta": str(hoy - timedelta(days=1))}).status_code == 422


def test_los_aportes_esperados_y_reales_aparecen_en_el_panel(escenario):
    """El panel incluye el resumen por integrante y los gastos sin repartir."""
    cuerpo = escenario["admin"].get(TABLERO).json()
    luis = next(i for i in cuerpo["aportes"] if i["nombre"] == "Luis")
    assert luis["aportes"] == "200000"
    assert cuerpo["gastos_sin_distribuir"] == "230000"  # no hay reglas: ningún gasto quedó repartido


def test_informe_mensual_json_coincide_con_el_panel(escenario):
    """El informe del mes trae los mismos totales y todos los movimientos, incluidas las reversiones."""
    admin = escenario["admin"]
    tablero = admin.get(TABLERO).json()
    informe = admin.get(MENSUAL, params={"mes": _mes_actual()}).json()
    assert informe["totales"] == tablero["totales"]
    assert informe["gastos_por_categoria"] == tablero["gastos_por_categoria"]
    assert informe["truncado"] is False and informe["total_movimientos"] == len(informe["movimientos"])
    tipos = [m["tipo"] for m in informe["movimientos"]]
    assert "reversion" in tipos and any(m["estado"] == "revertida" for m in informe["movimientos"])
    assert informe["total_movimientos"] == admin.get("/api/v1/transactions").json()["total"]


def test_informe_de_un_mes_pasado_y_meses_invalidos(escenario):
    """Un mes sin movimientos da totales en cero; formatos de mes inválidos se rechazan."""
    admin = escenario["admin"]
    vacio = admin.get(MENSUAL, params={"mes": "2020-02"}).json()
    assert vacio["total_movimientos"] == 0 and vacio["totales"]["gastos"] == "0" and vacio["hasta"] == "2020-02-29"
    for malo in ("2026-13", "2026-00", "26-05", "abril", "2026-5", "1999-12"):
        assert admin.get(MENSUAL, params={"mes": malo}).status_code == 422
    assert admin.get(MENSUAL).status_code == 422
    assert admin.get(MENSUAL, params={"mes": _mes_actual(), "formato": "xml"}).status_code == 422


def test_exportacion_csv(escenario):
    """El CSV se descarga con BOM y ';', respeta las tildes y neutraliza fórmulas de Excel."""
    admin = escenario["admin"]
    registrar_ok(admin, tipo="gasto", importe=1000, cuenta_origen_id=escenario["efectivo"]["id"], descripcion='=HYPERLINK("http://malo.example","clic")')
    respuesta = admin.get(MENSUAL, params={"mes": _mes_actual(), "formato": "csv"})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    assert f'informe-{_mes_actual()}.csv' in respuesta.headers["content-disposition"]
    texto = respuesta.content.decode("utf-8")
    assert texto.startswith("\ufeff")
    filas = list(csv.reader(io.StringIO(texto.lstrip("\ufeff")), delimiter=";"))
    assert filas[0] == ["fecha", "tipo", "estado", "categoria", "descripcion", "importe_cop", "cuentas"]
    assert len(filas) - 1 == admin.get(MENSUAL, params={"mes": _mes_actual()}).json()["total_movimientos"]
    assert any(f[3] == "Energía" for f in filas[1:])
    # La celda con fórmula quedó como texto inofensivo.
    peligrosa = next(f for f in filas[1:] if "HYPERLINK" in f[4])
    assert peligrosa[4].startswith("'=")
    # Los importes salen como números enteros, sin símbolos.
    assert all(f[5].isdigit() and int(f[5]) > 0 for f in filas[1:])


def test_la_exportacion_queda_auditada(escenario):
    """Exportar datos financieros es una acción sensible y se registra en la bitácora."""
    admin = escenario["admin"]
    admin.get(MENSUAL, params={"mes": _mes_actual(), "formato": "csv"})
    registros = [r for r in admin.get("/api/v1/audit", params={"limite": 100}).json()["items"] if r["accion"] == "informe_exportado"]
    assert len(registros) == 1 and registros[0]["detalle"]["mes"] == _mes_actual()


def test_permisos_de_informes(escenario, crear_miembro, nuevo_cliente, iniciar_sesion, cliente):
    """El miembro ve el panel y el informe JSON, pero no puede exportar CSV; sin sesión no hay acceso."""
    crear_miembro(escenario["hogar"], "Pablo Miembro", "pablo@example.com")
    pablo = iniciar_sesion(nuevo_cliente(), "pablo@example.com")
    assert pablo.get(TABLERO).status_code == 200
    assert pablo.get(MENSUAL, params={"mes": _mes_actual()}).status_code == 200
    assert pablo.get(MENSUAL, params={"mes": _mes_actual(), "formato": "csv"}).status_code == 403
    assert cliente.get(TABLERO).status_code == 401
    assert cliente.get(MENSUAL, params={"mes": _mes_actual()}).status_code == 401


def test_aislamiento_de_informes_entre_hogares(escenario, crear_hogar, nuevo_cliente, iniciar_sesion):
    """Otro hogar ve su propio panel vacío, sin rastro de las cifras del primero."""
    crear_hogar("Hogar B", "beto@example.com", "Beto Admin")
    admin_b = iniciar_sesion(nuevo_cliente(), "beto@example.com")
    cuerpo = admin_b.get(TABLERO).json()
    assert cuerpo["cuentas"] == [] and cuerpo["saldo_total"] == "0"
    assert cuerpo["totales"] == {"ingresos": "0", "aportes": "0", "gastos": "0", "pagos_de_prestamos": "0", "balance_operativo": "0"}
    assert cuerpo["proximos_vencimientos"] == [] and cuerpo["gastos_por_categoria"] == []
    informe = admin_b.get(MENSUAL, params={"mes": _mes_actual()}).json()
    assert informe["total_movimientos"] == 0
    assert admin_b.get(MENSUAL, params={"mes": _mes_actual(), "formato": "csv"}).content.decode().count("\r\n") == 1