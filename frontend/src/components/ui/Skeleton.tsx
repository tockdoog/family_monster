// frontend/src/components/ui/Skeleton.tsx
// Marcador de carga: ocupa el espacio mientras llegan los datos.

import { cn } from "@/lib/cn";

/** Bloque pulsante decorativo (oculto para lectores de pantalla). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-tarjeta bg-lavanda/30", className)} />;
}