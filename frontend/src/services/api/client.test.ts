// frontend/src/services/api/client.test.ts
// Pruebas del cliente HTTP: cookies, idempotencia, errores del backend y sesión vencida.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ErrorApi, api, registrarSesionExpirada } from "./client";

// Respuesta JSON simulada.
const json = (cuerpo: unknown, estado = 200) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

describe("cliente HTTP", () => {
  const fetchSimulado = vi.fn();
  beforeEach(() => vi.stubGlobal("fetch", fetchSimulado));
  afterEach(() => { fetchSimulado.mockReset(); registrarSesionExpirada(null); vi.unstubAllGlobals(); });

  it("envía la cookie de sesión y devuelve el cuerpo", async () => {
    fetchSimulado.mockResolvedValue(json({ ok: true }));
    expect(await api.get<{ ok: boolean }>("/algo")).toEqual({ ok: true });
    expect(fetchSimulado.mock.calls[0][0]).toBe("/api/v1/algo");
    expect(fetchSimulado.mock.calls[0][1].credentials).toBe("include");
  });

  it("envía la clave de idempotencia y el cuerpo JSON en los POST", async () => {
    fetchSimulado.mockResolvedValue(json({ id: 1 }, 201));
    await api.post("/transactions", { importe: 1000 }, "clave-1234-abcd");
    const opciones = fetchSimulado.mock.calls[0][1];
    expect(opciones.headers["Idempotency-Key"]).toBe("clave-1234-abcd");
    expect(opciones.headers["Content-Type"]).toBe("application/json");
    expect(opciones.body).toBe(JSON.stringify({ importe: 1000 }));
  });

  it("devuelve undefined en respuestas 204", async () => {
    fetchSimulado.mockResolvedValue(new Response(null, { status: 204 }));
    expect(await api.post("/auth/logout")).toBeUndefined();
  });

  it("convierte el error del backend en ErrorApi con su mensaje", async () => {
    fetchSimulado.mockResolvedValue(json({ error: { codigo: "conflicto", mensaje: "Ya existe una cuenta con ese nombre.", detalle: null } }, 409));
    const error = await api.post("/accounts", {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ErrorApi);
    expect(error).toMatchObject({ estado: 409, codigo: "conflicto", message: "Ya existe una cuenta con ese nombre." });
  });

  it("usa un mensaje seguro cuando el backend no entrega uno legible", async () => {
    fetchSimulado.mockResolvedValue(new Response("<html>caída</html>", { status: 403 }));
    const error = await api.get("/x").catch((e: unknown) => e as ErrorApi);
    expect((error as ErrorApi).message).toBe("No tienes permiso para realizar esta acción.");
  });

  it("avisa que no hay conexión cuando falla la red", async () => {
    fetchSimulado.mockRejectedValue(new TypeError("fallo"));
    const error = await api.get("/x").catch((e: unknown) => e as ErrorApi);
    expect(error).toMatchObject({ estado: 0, codigo: "sin_conexion" });
  });

  it("notifica la sesión vencida con un 401, salvo en el login", async () => {
    const alVencer = vi.fn();
    registrarSesionExpirada(alVencer);
    fetchSimulado.mockImplementation(() => Promise.resolve(json({ error: { codigo: "no_autenticado", mensaje: "x" } }, 401)));
    await api.get("/accounts").catch(() => undefined);
    expect(alVencer).toHaveBeenCalledTimes(1);
    await api.post("/auth/login", {}).catch(() => undefined);
    expect(alVencer).toHaveBeenCalledTimes(1);
  });
});