// frontend/src/lib/formatCOP.test.ts
// Pruebas del formato de pesos colombianos.

import { describe, expect, it } from "vitest";
import { formatCOP } from "./formatCOP";

// Intl usa espacios especiales entre el símbolo y el número: se normalizan para comparar.
const limpio = (t: string) => t.replace(/\s/g, " ");

describe("formatCOP", () => {
  it("usa punto como separador de miles y no muestra decimales", () => {
    expect(limpio(formatCOP(1250000))).toContain("1.250.000");
    expect(formatCOP(1250000)).not.toContain(",");
  });

  it("acepta el texto de pesos enteros que envía el backend", () => {
    expect(limpio(formatCOP("500000"))).toContain("500.000");
  });

  it("muestra los negativos con signo", () => {
    expect(formatCOP(-50000)).toContain("-");
  });

  it("devuelve una raya cuando el valor no es válido", () => {
    expect(formatCOP(null)).toBe("—");
    expect(formatCOP(undefined)).toBe("—");
    expect(formatCOP("")).toBe("—");
    expect(formatCOP("abc")).toBe("—");
  });
});