// frontend/src/features/dashboard/components/IndicadorCard.tsx
// Tarjeta de un indicador: nombre, explicación, monto en COP y entrada animada.

import type { LucideIcon } from "lucide-react";
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Ayuda } from "@/components/ui/Ayuda";
import { Card } from "@/components/ui/Card";
import { formatCOP } from "@/lib/formatCOP";

interface Props {
  etiqueta: string;
  ayuda: string;
  valor: string;
  icono: LucideIcon;
  detalle?: ReactNode;
  retraso?: number;
}

/** Indicador financiero; el valor ya viene calculado por el backend. */
export function IndicadorCard({ etiqueta, ayuda, valor, icono: Icono, detalle, retraso = 0 }: Props) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: retraso }}>
      <Card className="h-full">
        <div className="flex items-center justify-between text-morado-secundario">
          <span className="flex items-center gap-1 text-sm font-semibold">
            {etiqueta}
            <Ayuda texto={ayuda} />
          </span>
          <Icono size={22} aria-hidden />
        </div>
        <p className="cifras mt-2 text-2xl font-extrabold text-morado">{formatCOP(valor)}</p>
        {detalle && <div className="mt-1 text-sm text-texto-suave">{detalle}</div>}
      </Card>
    </motion.div>
  );
}