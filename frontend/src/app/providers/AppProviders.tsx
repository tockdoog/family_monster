// frontend/src/app/providers/AppProviders.tsx
// Agrupa los proveedores globales: caché de datos, animaciones accesibles y sesión.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { useState, type ReactNode } from "react";
import { AuthProvider } from "./AuthProvider";

/** Proveedores globales de la aplicación. */
export function AppProviders({ children }: { children: ReactNode }) {
  // Sin reintentos automáticos ni recarga al enfocar: evita repetir operaciones y llamadas innecesarias.
  const [cliente] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } }),
  );
  return (
    <QueryClientProvider client={cliente}>
      {/* "user" respeta prefers-reduced-motion del sistema operativo */}
      <MotionConfig reducedMotion="user">
        <AuthProvider>{children}</AuthProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}