// frontend/src/app/providers/AppProviders.tsx
// Proveedores globales: caché de datos, animaciones accesibles, sesión y avisos de éxito.

import { MutationCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { useState, type ReactNode } from "react";
import { Avisos } from "@/components/feedback/Avisos";
import { avisar } from "@/lib/avisos";
import { AuthProvider } from "./AuthProvider";

/** Proveedores globales de la aplicación. */
export function AppProviders({ children }: { children: ReactNode }) {
  const [cliente] = useState(
    () =>
      new QueryClient({
        // Cada mutación puede declarar meta.exito: al confirmarse en el backend se muestra ese aviso.
        mutationCache: new MutationCache({
          onSuccess: (_datos, _variables, _contexto, mutacion) => {
            const texto = mutacion.meta?.exito;
            if (typeof texto === "string") avisar(texto);
          },
        }),
        // Sin reintentos automáticos ni recarga al enfocar: evita repetir operaciones y llamadas innecesarias.
        defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <QueryClientProvider client={cliente}>
      {/* "user" respeta prefers-reduced-motion del sistema operativo */}
      <MotionConfig reducedMotion="user">
        <AuthProvider>{children}</AuthProvider>
        <Avisos />
      </MotionConfig>
    </QueryClientProvider>
  );
}