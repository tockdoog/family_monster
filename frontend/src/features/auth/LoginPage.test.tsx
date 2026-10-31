// frontend/src/features/auth/LoginPage.test.tsx
// Pruebas del inicio de sesión: validaciones, errores del backend y envío correcto.

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/app/providers/AuthProvider";
import { ErrorApi } from "@/services/api/client";
import { LoginPage } from "./LoginPage";

vi.mock("@/app/providers/AuthProvider", () => ({ useAuth: vi.fn() }));
type ValorAuth = ReturnType<typeof useAuth>;
const entrar = vi.fn();

// Monta la pantalla sin sesión.
const montar = () => {
  vi.mocked(useAuth).mockReturnValue({ sesion: null, cargando: false, entrar } as unknown as ValorAuth);
  return render(<MemoryRouter><LoginPage /></MemoryRouter>);
};
// Llena el formulario y lo envía.
const enviar = (email: string, contrasena: string) => {
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText(/^Contraseña$/), { target: { value: contrasena } });
  fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
};

describe("LoginPage", () => {
  beforeEach(() => {
    entrar.mockReset();
  });

  it("muestra validaciones y no llama al backend con el formulario vacío", async () => {
    montar();
    fireEvent.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Escribe tu correo.")).toBeTruthy();
    expect(screen.getByText("Escribe tu contraseña.")).toBeTruthy();
    expect(entrar).not.toHaveBeenCalled();
  });

  it("rechaza un correo mal escrito", async () => {
    montar();
    enviar("no-es-correo", "ClaveSegura123");
    expect(await screen.findByText("Escribe un correo válido.")).toBeTruthy();
    expect(entrar).not.toHaveBeenCalled();
  });

  it("muestra el mensaje del backend cuando las credenciales son incorrectas", async () => {
    entrar.mockRejectedValue(new ErrorApi(401, "no_autenticado", "Correo o contraseña incorrectos."));
    montar();
    enviar("ana@correo.com", "ClaveMala123");
    expect((await screen.findByRole("alert")).textContent).toContain("Correo o contraseña incorrectos.");
  });

  it("envía las credenciales al proveedor de sesión", async () => {
    entrar.mockResolvedValue(undefined);
    montar();
    enviar("ana@correo.com", "ClaveSegura123");
    await waitFor(() => expect(entrar).toHaveBeenCalledWith("ana@correo.com", "ClaveSegura123"));
  });

  it("permite mostrar y ocultar la contraseña", () => {
    montar();
    const campo = screen.getByLabelText(/^Contraseña$/) as HTMLInputElement;
    expect(campo.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(campo.type).toBe("text");
  });
});