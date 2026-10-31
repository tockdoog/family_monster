// frontend/src/app/providers/AuthProvider.tsx
// Estado de sesión para toda la app. La verdad la tiene el backend: aquí solo se guarda lo que responde.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { registrarSesionExpirada } from "@/services/api/client";
import { cerrarSesion, consultarSesion, iniciarSesion } from "@/services/auth/authApi";
import type { Sesion } from "@/types/api";

interface ValorAuth {
  sesion: Sesion | null;
  cargando: boolean;
  entrar: (email: string, contrasena: string) => Promise<void>;
  salir: () => Promise<void>;
  puede: (permiso: string) => boolean;
}

const Contexto = createContext<ValorAuth | null>(null);

/** Proveedor de sesión: al abrir la app pregunta al backend si ya hay una sesión válida. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [cargando, setCargando] = useState(true);

  // Carga inicial y reacción a sesiones vencidas (401 en cualquier petición).
  useEffect(() => {
    let activo = true;
    const control = new AbortController();
    registrarSesionExpirada(() => setSesion(null));
    consultarSesion(control.signal)
      .then((s) => activo && setSesion(s))
      .catch(() => activo && setSesion(null))
      .finally(() => activo && setCargando(false));
    return () => {
      activo = false;
      control.abort();
      registrarSesionExpirada(null);
    };
  }, []);

  // Inicio de sesión: si falla, el error llega al formulario para mostrarlo.
  const entrar = useCallback(async (email: string, contrasena: string) => {
    setSesion(await iniciarSesion(email, contrasena));
  }, []);

  // Cierre de sesión: la sesión local se limpia aunque falle la red.
  const salir = useCallback(async () => {
    try {
      await cerrarSesion();
    } finally {
      setSesion(null);
    }
  }, []);

  // Solo para mostrar u ocultar opciones; el backend valida cada petición.
  const puede = useCallback((permiso: string) => sesion?.permisos.includes(permiso) ?? false, [sesion]);

  const valor = useMemo(() => ({ sesion, cargando, entrar, salir, puede }), [sesion, cargando, entrar, salir, puede]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

/** Acceso a la sesión desde cualquier componente. */
export function useAuth(): ValorAuth {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useAuth debe usarse dentro de AuthProvider.");
  return valor;
}