// frontend/src/features/loans/schemas.test.ts
// Pruebas de las reglas de préstamos según su tipo.

import { describe, expect, it } from "vitest";
import { aSolicitudPagoCuota, aSolicitudPrestamo, esquemaPagoCuota, esquemaPrestamo, type DatosPrestamo } from "./schemas";

// Préstamo vacío: cada prueba completa lo que necesita.
const base: DatosPrestamo = { tipo: "entre_integrantes", importe: "1.000.000", numeroCuotas: "4", totalAPagar: "", prestamistaId: "", prestatarioId: "", contraparteNombre: "", cuentaOrigenId: "", cuentaDestinoId: "", fecha: "", primerVencimiento: "", condiciones: "" };
const errores = (d: DatosPrestamo) => { const r = esquemaPrestamo.safeParse(d); return r.success ? [] : r.error.issues.map((i) => i.path.join(".")); };

describe("esquemaPrestamo", () => {
  it("entre integrantes exige ambas partes y ambas cuentas", () => {
    expect(errores(base)).toEqual(expect.arrayContaining(["prestamistaId", "prestatarioId", "cuentaOrigenId", "cuentaDestinoId"]));
  });
  it("entre integrantes rechaza que presten y reciban la misma persona", () => {
    expect(errores({ ...base, prestamistaId: "a", prestatarioId: "a", cuentaOrigenId: "o", cuentaDestinoId: "d" })).toContain("prestatarioId");
  });
  it("al hogar acepta un tercero por nombre y exige el fondo común que recibe", () => {
    expect(errores({ ...base, tipo: "al_hogar" })).toEqual(expect.arrayContaining(["contraparteNombre", "cuentaDestinoId"]));
    expect(errores({ ...base, tipo: "al_hogar", contraparteNombre: "Banco", cuentaDestinoId: "c1" })).toEqual([]);
  });
  it("limita las cuotas entre 1 y 360", () => {
    for (const malo of ["0", "361", "x", ""]) expect(errores({ ...base, numeroCuotas: malo })).toContain("numeroCuotas");
  });
});

describe("aSolicitudPrestamo", () => {
  it("en un préstamo al hogar con tercero envía el nombre y solo la cuenta de destino", () => {
    const cuerpo = aSolicitudPrestamo({ ...base, tipo: "al_hogar", contraparteNombre: "Banco", cuentaDestinoId: "c1", cuentaOrigenId: "stale" });
    expect(cuerpo).toMatchObject({ tipo: "al_hogar", importe: 1000000, numero_cuotas: 4, contraparte_nombre: "Banco", cuenta_destino_id: "c1" });
    expect(cuerpo.cuenta_origen_id).toBeUndefined();
    expect(cuerpo.prestamista_integrante_id).toBeUndefined();
  });
});

describe("pago de cuota", () => {
  it("un préstamo del hogar solo pide la cuenta que recibe", () => {
    const r = esquemaPagoCuota("del_hogar").safeParse({ cuotaNumero: "1", importe: "100.000", cuentaOrigenId: "", cuentaDestinoId: "c1", fecha: "" });
    expect(r.success).toBe(true);
    expect(aSolicitudPagoCuota("del_hogar", { cuotaNumero: "1", importe: "100.000", cuentaOrigenId: "x", cuentaDestinoId: "c1", fecha: "" })).toEqual({ cuota_numero: 1, importe: 100000, cuenta_origen_id: undefined, cuenta_destino_id: "c1", fecha: undefined });
  });
  it("entre integrantes exige origen y destino", () => {
    expect(esquemaPagoCuota("entre_integrantes").safeParse({ cuotaNumero: "1", importe: "5.000", cuentaOrigenId: "", cuentaDestinoId: "", fecha: "" }).success).toBe(false);
  });
});