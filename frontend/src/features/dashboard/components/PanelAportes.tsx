// frontend/src/features/dashboard/components/PanelAportes.tsx
// Estado de aportes por integrante. Cifras y estado vienen del backend; el porcentaje es solo visual.

import { Badge } from "@/components/ui/Badge";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { formatCOP } from "@/lib/formatCOP";
import type { ResumenIntegrante } from "@/types/finanzas";

/** Una fila por integrante, sin ordenar por monto para evitar comparaciones entre la familia. */
export function PanelAportes({ integrantes }: { integrantes: ResumenIntegrante[] }) {
  if (integrantes.length === 0) {
    return <EstadoVacio titulo="Sin aportes por mostrar" texto="Cuando definas la regla de reparto, verás aquí cómo va cada integrante." />;
  }
  return (
    <ul className="space-y-4">
      {integrantes.map((i) => {
        const esperado = Number(i.obligacion_esperada);
        const porcentaje = esperado > 0 ? Math.min(100, Math.round((Number(i.aportado_neto) / esperado) * 100)) : null;
        return (
          <li key={i.integrante_id}>
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-texto">{i.nombre}</p>
              <Badge tono={i.estado === "al_dia" ? "exito" : "aviso"}>{i.estado === "al_dia" ? "Al día" : "Pendiente"}</Badge>
            </div>
            {porcentaje !== null && (
              <div
                role="progressbar"
                aria-valuenow={porcentaje}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Aportes de ${i.nombre}`}
                className="mt-2 h-2.5 overflow-hidden rounded-full bg-lavanda/30"
              >
                <div className="h-full rounded-full bg-violeta transition-[width] duration-700" style={{ width: `${porcentaje}%` }} />
              </div>
            )}
            <p className="cifras mt-1 text-sm text-texto-suave">
              Ha aportado {formatCOP(i.aportado_neto)} de {formatCOP(i.obligacion_esperada)}
            </p>
          </li>
        );
      })}
    </ul>
  );
}