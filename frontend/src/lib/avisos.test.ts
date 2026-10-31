// frontend/src/lib/avisos.test.ts
// Pruebas de los avisos de éxito: aparecen y se retiran solos.

import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { avisar, quitarAviso, useAvisos } from "./avisos";

describe("avisos", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("muestra un aviso y lo retira solo a los 4 segundos", () => {
    const { result } = renderHook(() => useAvisos());
    act(() => avisar("Movimiento registrado"));
    expect(result.current.map((a) => a.texto)).toContain("Movimiento registrado");
    act(() => { vi.advanceTimersByTime(4100); });
    expect(result.current.map((a) => a.texto)).not.toContain("Movimiento registrado");
  });

  it("permite quitar un aviso manualmente y mantiene los demás", () => {
    const { result } = renderHook(() => useAvisos());
    act(() => { avisar("Uno"); avisar("Dos"); });
    const uno = result.current.find((a) => a.texto === "Uno")!;
    act(() => quitarAviso(uno.id));
    expect(result.current.map((a) => a.texto)).toEqual(["Dos"]);
    act(() => { vi.advanceTimersByTime(4100); });
  });
});