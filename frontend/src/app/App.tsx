// frontend/src/app/App.tsx
// Componente raíz: proveedores globales y enrutador.

import { RouterProvider } from "react-router-dom";
import { AppProviders } from "./providers/AppProviders";
import { router } from "./router";

/** Raíz de la aplicación. */
export default function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}