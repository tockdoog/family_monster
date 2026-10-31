// frontend/src/features/dashboard/components/PanelVencimientos.tsx
// Obligaciones y cuotas próximas a vencer (o ya vencidas) con saldo por pagar.

import { Badge } from "@/components/ui/Badge";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import type { Vencimiento } from "../types";

/** Lista de vencimientos; el estado se indica con texto, no solo con color. */
export function PanelVencimientos({ vencimientos }: { vencimientos: Vencimiento[] }) {
  if (vencimientos.length === 0) {
    return <EstadoVacio titulo="Todo al día" texto="No hay facturas ni cuotas por vencer en los próximos días." />;
  }
  return (
    <ul className="divide-y divide-lavanda/30">
      {vencimientos.map((v) => (
        <li key={`${v.tipo}-${v.referencia_id}`} className="flex items-center justify-between gap-3 py-3">
          <div>
            <p className="font-semibold text-texto">{v.descripcion}</p>
            <p className="text-sm text-texto-suave">
              {v.tipo === "cuota" ? "Cuota de préstamo" : "Obligación"} · {formatFechaCorta(v.fecha_vencimiento)}
            </p>
          </div>
          <div className="text-right">
            <p className="cifras font-bold text-morado">{formatCOP(v.saldo)}</p>
            <Badge tono={v.vencido ? "alerta" : "aviso"}>{v.vencido ? "Vencido" : "Próximo"}</Badge>
          </div>
        </li>
      ))}
    </ul>
  );
}