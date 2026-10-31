// frontend/src/components/ui/Card.tsx
// Tarjeta blanca con borde redondeado y sombra suave. Con "elevable" se levanta un poco al pasar el cursor.

import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface Props extends HTMLAttributes<HTMLDivElement> {
  elevable?: boolean;
}

/** Contenedor visual reutilizable. */
export function Card({ className, elevable = false, ...resto }: Props) {
  return (
    <div
      {...resto}
      className={cn("rounded-tarjeta bg-blanco p-5 shadow-tarjeta", elevable && "transition duration-200 hover:-translate-y-0.5 hover:shadow-lg", className)}
    />
  );
}