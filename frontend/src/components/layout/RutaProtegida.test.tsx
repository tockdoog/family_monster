// frontend/src/components/layout/RutaProtegida.test.tsx
// Pruebas de la protección de rutas privadas.

import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/app/providers/AuthProvider";
import { RutaProtegida } from "./RutaProtegida";

vi.mock("@/app/providers/AuthProvider", () => ({ useAuth: vi.fn() }));
type ValorAuth = ReturnType<typeof useAuth>;
const sesion = { usuario: { id: "u1", email: "ana@correo.com", nombre_completo: "Ana Gómez" }, hogar: { id: "h1", nombre: "Casa" }, rol: "miembro", permisos: ["ver_finanzas"] };

// Monta una ruta privada y la pantalla de ingreso.
const montar = () => render(
  <MemoryRouter initialEntries={["/panel"]}>
    <Routes>
      <Route element={<RutaProtegida />}><Route path="/panel" element={<p>Contenido privado</p>} /></Route>
      <Route path="/ingresar" element={<p>Pantalla de ingreso</p>} />
    </Routes>
  </MemoryRouter>,
);

describe("RutaProtegida", () => {
  beforeEach(() => {
    vi.mocked(useAuth).mockReset();
  });

  it("espera mientras se consulta la sesión, sin mostrar el ingreso", () => {
    vi.mocked(useAuth).mockReturnValue({ sesion: null, cargando: true } as ValorAuth);
    montar();
    expect(screen.getByRole("status").textContent).toContain("Cargando");
    expect(screen.queryByText("Pantalla de ingreso")).toBeNull();
  });

  it("redirige al ingreso cuando no hay sesión", () => {
    vi.mocked(useAuth).mockReturnValue({ sesion: null, cargando: false } as ValorAuth);
    montar();
    expect(screen.getByText("Pantalla de ingreso")).toBeTruthy();
    expect(screen.queryByText("Contenido privado")).toBeNull();
  });

  it("muestra el contenido con sesión activa", () => {
    vi.mocked(useAuth).mockReturnValue({ sesion, cargando: false } as ValorAuth);
    montar();
    expect(screen.getByText("Contenido privado")).toBeTruthy();
  });
});