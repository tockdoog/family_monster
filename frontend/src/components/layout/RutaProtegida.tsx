// frontend/src/components/layout/RutaProtegida.tsx
// Guardia de rutas privadas: sin sesión, redirige al ingreso. El backend igual valida cada petición.

import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";

/** Muestra las rutas hijas solo si hay sesión activa. */
export function RutaProtegida() {
  const { sesion, cargando } = useAuth();
  const ubicacion = useLocation();

  // Mientras se consulta /auth/me no se decide nada, para no mostrar el login por error.
  if (cargando) {
    return (
      <p role="status" className="grid min-h-screen place-items-center text-texto-suave">
        Cargando…
      </p>
    );
  }
  if (!sesion) return <Navigate to="/ingresar" replace state={{ desde: ubicacion.pathname }} />;
  return <Outlet />;
}