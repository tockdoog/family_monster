// frontend/src/components/ui/Badge.tsx
// Etiqueta de estado. Siempre lleva texto: el color nunca es el único indicador.

import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

// Tonos permitidos: los de estado financiero se reservan para estados reales.
type Tono = "neutro" | "exito" | "alerta" | "aviso";

const ESTILOS: Record<Tono, string> = {
  neutro: "bg-lavanda/25 text-morado",
  exito: "bg-exito/15 text-green-800",
  alerta: "bg-alerta/15 text-red-800",
  aviso: "bg-aviso/20 text-amber-900",
};

/** Etiqueta redondeada con tono según el estado. */
export function Badge({ tono = "neutro", children }: { tono?: Tono; children: ReactNode }) {
  return (
    <span className={cn("inline-flex rounded-full px-3 py-1 text-sm font-semibold", ESTILOS[tono])}>
      {children}
    </span>
  );
}