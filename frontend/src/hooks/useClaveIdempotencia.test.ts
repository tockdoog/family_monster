// frontend/src/hooks/useClaveIdempotencia.test.ts
// Pruebas de la clave de idempotencia: estable en reintentos, nueva tras un rechazo del backend.

import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErrorApi } from "@/services/api/client";
import { useClaveIdempotencia } from "./useClaveIdempotencia";

// Formato que exige el backend (shared/idempotency.py).
const PATRON = /^[A-Za-z0-9_-]{8,80}$/;

describe("useClaveIdempotencia", () => {
  it("genera una clave con el formato que acepta el backend", () => {
    const { result } = renderHook(() => useClaveIdempotencia());
    expect(result.current.obtener()).toMatch(PATRON);
  });

  it("conserva la clave si falla la red o el servidor (el envío pudo aplicarse)", () => {
    const { result } = renderHook(() => useClaveIdempotencia());
    const antes = result.current.obtener();
    result.current.alFallar(new ErrorApi(0, "sin_conexion", "x"));
    result.current.alFallar(new ErrorApi(500, "error_interno", "x"));
    expect(result.current.obtener()).toBe(antes);
  });

  it("renueva la clave si el backend rechazó la solicitud (4xx)", () => {
    const { result } = renderHook(() => useClaveIdempotencia());
    const antes = result.current.obtener();
    result.current.alFallar(new ErrorApi(422, "regla_de_negocio", "x"));
    expect(result.current.obtener()).not.toBe(antes);
    expect(result.current.obtener()).toMatch(PATRON);
  });
});