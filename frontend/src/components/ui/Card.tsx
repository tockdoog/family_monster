// frontend/src/components/ui/Card.tsx
// Tarjeta blanca con borde redondeado y sombra suave: contenedor base de toda la interfaz.

import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/** Contenedor visual reutilizable. */
export function Card({ className, ...resto }: HTMLAttributes<HTMLDivElement>) {
  return <div {...resto} className={cn("rounded-tarjeta bg-blanco p-5 shadow-tarjeta", className)} />;
}