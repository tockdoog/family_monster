// frontend/src/app/router.tsx
// Mapa de rutas: públicas (bienvenida, ingreso) y privadas (dentro del layout con sesión).

import { Navigate, createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { RutaProtegida } from "@/components/layout/RutaProtegida";
import { CuentasPage } from "@/features/accounts/CuentasPage";
import { BienvenidaPage } from "@/features/auth/BienvenidaPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { AportesPage } from "@/features/contributions/AportesPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { IntegrantesPage } from "@/features/members/IntegrantesPage";
import { ConfiguracionPage } from "@/features/settings/ConfiguracionPage";
import { InformesPage } from "@/features/reports/InformesPage";
import { PrestamosPage } from "@/features/loans/PrestamosPage";
import { ObligacionesPage } from "@/features/obligations/ObligacionesPage";
import { MovimientosPage } from "@/features/transactions/MovimientosPage";

export const router = createBrowserRouter([
  // Rutas públicas
  { path: "/", element: <BienvenidaPage /> },
  { path: "/ingresar", element: <LoginPage /> },
  // Rutas privadas: exigen sesión y comparten el layout
  {
    element: <RutaProtegida />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/panel", element: <DashboardPage /> },
          { path: "/cuentas", element: <CuentasPage /> },
          { path: "/movimientos", element: <MovimientosPage /> },
          { path: "/aportes", element: <AportesPage /> },
          { path: "/obligaciones", element: <ObligacionesPage /> },
          { path: "/prestamos", element: <PrestamosPage /> },
          { path: "/informes", element: <InformesPage /> },
          { path: "/integrantes", element: <IntegrantesPage /> },
          { path: "/configuracion", element: <ConfiguracionPage /> },
        ],
      },
    ],
  },
  // Cualquier ruta desconocida vuelve al inicio
  { path: "*", element: <Navigate to="/" replace /> },
]);