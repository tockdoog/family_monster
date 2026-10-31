// frontend/src/components/layout/RutaProtegida.tsx
// Protege las rutas privadas: espera a conocer la sesión, redirige al ingreso si no hay una y,
// si la hay, muestra la ruta hija. La seguridad real la valida el backend en cada petición.

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";

/** Guardia de rutas privadas. Se usa como elemento de una ruta con hijas (<Outlet />). */
export function RutaProtegida() {
  const { sesion, cargando } = useAuth();

  // Mientras se consulta la sesión no se redirige: evita mandar al ingreso a quien ya tiene sesión.
  if (cargando) {
    return (
      <div role="status" className="grid min-h-screen place-items-center bg-fondo text-texto-suave">
        Cargando…
      </div>
    );
  }

  // Sin sesión válida: al ingreso, reemplazando la entrada del historial para que "Atrás" no vuelva aquí.
  if (!sesion) return <Navigate to="/ingresar" replace />;

  // Con sesión: se muestra la ruta privada que corresponda.
  return <Outlet />;
}