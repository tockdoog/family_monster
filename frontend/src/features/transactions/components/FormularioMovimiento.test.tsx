// frontend/src/features/transactions/components/FormularioMovimiento.test.tsx
// Pruebas del registro de movimientos: confirmación previa, cuerpo enviado y clave de idempotencia.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FormularioMovimiento } from "./FormularioMovimiento";

// Datos simulados de los hooks que consultan la API.
const registrar = vi.fn();
vi.mock("@/features/accounts/api", () => ({ useCuentas: () => ({ data: [{ id: "c1", nombre: "Efectivo", tipo: "efectivo", es_fondo_comun: true, propietario_id: null, saldo_inicial: "0", saldo_actual: "0", activa: true }] }) }));
vi.mock("@/features/categories/api", () => ({ useCategorias: () => ({ data: [] }) }));
vi.mock("@/features/members/api", () => ({ useIntegrantes: () => ({ data: [] }) }));
vi.mock("../api", () => ({ useRegistrarMovimiento: () => ({ mutateAsync: registrar, isPending: false }) }));

// Llena un gasto válido y pulsa "Revisar".
const llenarYRevisar = () => {
  fireEvent.change(screen.getByLabelText("Importe (COP)"), { target: { value: "50.000" } });
  fireEvent.change(screen.getByLabelText("Descripción"), { target: { value: "Mercado" } });
  fireEvent.change(screen.getByLabelText("Cuenta de origen"), { target: { value: "c1" } });
  fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
};

describe("FormularioMovimiento", () => {
  beforeEach(() => {
    registrar.mockReset().mockResolvedValue({});
  });

  it("no envía nada al revisar: primero pide confirmación", async () => {
    render(<FormularioMovimiento onListo={vi.fn()} onCancelar={vi.fn()} />);
    llenarYRevisar();
    expect(await screen.findByRole("button", { name: "Confirmar y registrar" })).toBeTruthy();
    expect(registrar).not.toHaveBeenCalled();
  });

  it("al confirmar envía el cuerpo correcto con una clave de idempotencia válida y cierra", async () => {
    const onListo = vi.fn();
    render(<FormularioMovimiento onListo={onListo} onCancelar={vi.fn()} />);
    llenarYRevisar();
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar y registrar" }));
    await waitFor(() => expect(onListo).toHaveBeenCalled());
    const { datos, clave } = registrar.mock.calls[0][0];
    expect(datos).toMatchObject({ tipo: "gasto", importe: 50000, descripcion: "Mercado", cuenta_origen_id: "c1" });
    expect(clave).toMatch(/^[A-Za-z0-9_-]{8,80}$/);
  });

  it("si el backend rechaza el registro, vuelve al formulario con el mensaje y no cierra", async () => {
    const { ErrorApi } = await import("@/services/api/client");
    registrar.mockRejectedValue(new ErrorApi(422, "regla_de_negocio", "Saldo insuficiente."));
    const onListo = vi.fn();
    render(<FormularioMovimiento onListo={onListo} onCancelar={vi.fn()} />);
    llenarYRevisar();
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar y registrar" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Saldo insuficiente.");
    expect(onListo).not.toHaveBeenCalled();
  });

  it("muestra errores de validación sin pasar a la confirmación", async () => {
    render(<FormularioMovimiento onListo={vi.fn()} onCancelar={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Revisar" }));
    expect(await screen.findByText("Escribe un importe en pesos enteros mayor que cero.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Confirmar y registrar" })).toBeNull();
  });
});