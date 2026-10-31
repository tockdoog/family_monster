// frontend/src/app/router.tsx
// Mapa de rutas: públicas (bienvenida, ingreso) y privadas (dentro del layout con sesión).

import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { RutaProtegida } from "@/components/layout/RutaProtegida";
import { BienvenidaPage } from "@/features/auth/BienvenidaPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";

export const router = createBrowserRouter([
  // Rutas públicas
  { path: "/", element: <BienvenidaPage /> },
  { path: "/ingresar", element: <LoginPage /> },
  // Rutas privadas: exigen sesión y comparten el layout
  {
    element: <RutaProtegida />,
    children: [{ element: <AppLayout />, children: [{ path: "/panel", element: <DashboardPage /> }] }],
  },
  // Cualquier ruta desconocida vuelve al inicio
  { path: "*", element: <Navigate to="/" replace /> },
]);