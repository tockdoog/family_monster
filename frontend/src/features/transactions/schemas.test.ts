// frontend/src/features/transactions/schemas.test.ts
// Pruebas de las reglas de movimientos y del cuerpo que se envía a la API.

import { describe, expect, it } from "vitest";
import { aSolicitud, esquemaMovimiento, esquemaReversion, type DatosMovimiento } from "./schemas";

// Datos válidos de un gasto, base para cada caso.
const gasto: DatosMovimiento = { tipo: "gasto", importe: "50.000", descripcion: "Mercado", fecha: "", cuentaOrigenId: "c1", cuentaDestinoId: "", categoriaId: "", pagadorId: "" };
// Campos con error de un resultado fallido.
const camposConError = (d: DatosMovimiento) => {
  const r = esquemaMovimiento.safeParse(d);
  return r.success ? [] : r.error.issues.map((i) => i.path.join("."));
};

describe("esquemaMovimiento", () => {
  it("acepta un gasto completo", () => expect(esquemaMovimiento.safeParse(gasto).success).toBe(true));
  it("exige cuenta de origen en un gasto", () => expect(camposConError({ ...gasto, cuentaOrigenId: "" })).toContain("cuentaOrigenId"));
  it("exige cuenta de destino en un ingreso", () => expect(camposConError({ ...gasto, tipo: "ingreso", cuentaOrigenId: "" })).toContain("cuentaDestinoId"));
  it("exige dos cuentas distintas en una transferencia", () => {
    expect(camposConError({ ...gasto, tipo: "transferencia", cuentaDestinoId: "c1" })).toContain("cuentaDestinoId");
    expect(esquemaMovimiento.safeParse({ ...gasto, tipo: "transferencia", cuentaDestinoId: "c2" }).success).toBe(true);
  });
  it("rechaza importes con centavos, cero o texto", () => {
    for (const malo of ["0", "10,5", "abc", ""]) expect(camposConError({ ...gasto, importe: malo })).toContain("importe");
  });
  it("rechaza fechas futuras", () => expect(camposConError({ ...gasto, fecha: "2999-01-01" })).toContain("fecha"));
});

describe("aSolicitud", () => {
  it("convierte el importe a número y omite lo que no aplica al tipo", () => {
    const cuerpo = aSolicitud({ ...gasto, cuentaDestinoId: "stale", categoriaId: "cat1", pagadorId: "p1" });
    expect(cuerpo).toMatchObject({ tipo: "gasto", importe: 50000, cuenta_origen_id: "c1", categoria_id: "cat1", pagador_id: "p1" });
    expect(cuerpo.cuenta_destino_id).toBeUndefined();
  });
  it("en una transferencia no envía categoría ni pagador", () => {
    const cuerpo = aSolicitud({ ...gasto, tipo: "transferencia", cuentaDestinoId: "c2", categoriaId: "cat1", pagadorId: "p1" });
    expect(cuerpo.categoria_id).toBeUndefined();
    expect(cuerpo.pagador_id).toBeUndefined();
  });
});

describe("esquemaReversion", () => {
  it("exige un motivo de al menos 5 caracteres reales", () => {
    expect(esquemaReversion.safeParse({ motivo: "  ab  " }).success).toBe(false);
    expect(esquemaReversion.safeParse({ motivo: "Error de digitación" }).success).toBe(true);
  });
});