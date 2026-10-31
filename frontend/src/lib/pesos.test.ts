// frontend/src/lib/pesos.test.ts
// Pruebas de la interpretación de importes escritos por el usuario.

import { describe, expect, it } from "vitest";
import { esImportePositivo, normalizarPesos } from "./pesos";

describe("normalizarPesos", () => {
  it("quita puntos, espacios y el símbolo $", () => {
    expect(normalizarPesos("$ 1.500.000")).toBe("1500000");
  });
});

describe("esImportePositivo", () => {
  it("acepta pesos enteros mayores que cero", () => {
    expect(esImportePositivo("50.000")).toBe(true);
    expect(esImportePositivo("1")).toBe(true);
  });

  it("rechaza cero, negativos, centavos, comas y texto", () => {
    for (const malo of ["0", "-5", "10,5", "abc", "", "1000000000000"]) expect(esImportePositivo(malo)).toBe(false);
  });
});