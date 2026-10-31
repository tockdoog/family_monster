// frontend/src/components/ui/BarraProgreso.tsx
// Barra de progreso accesible que se llena con una animación suave. El porcentaje es solo visual.

import { motion } from "motion/react";
import { cn } from "@/lib/cn";

interface Props {
  porcentaje: number;
  etiqueta: string;
  className?: string;
}

/** Se anima de 0 al porcentaje al aparecer. */
export function BarraProgreso({ porcentaje, etiqueta, className }: Props) {
  return (
    <div role="progressbar" aria-valuenow={porcentaje} aria-valuemin={0} aria-valuemax={100} aria-label={etiqueta}
      className={cn("h-2.5 overflow-hidden rounded-full bg-lavanda/30", className)}>
      <motion.div className="h-full rounded-full bg-violeta" initial={{ width: 0 }} animate={{ width: `${porcentaje}%` }} transition={{ duration: 0.8, ease: "easeOut" }} />
    </div>
  );
}