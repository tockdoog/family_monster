// frontend/src/features/loans/components/DetallePrestamo.tsx
// Cuotas e historial de pagos de un préstamo (GET /loans/{id}).

import { Badge } from "@/components/ui/Badge";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { mensajeError } from "@/lib/errores";
import { usePrestamo } from "../api";
import { ETIQUETA_ESTADO_CUOTA, TONO_CUOTA } from "../types";

/** Detalle con cuotas y pagos; los pagos revertidos se marcan como tales. */
export function DetallePrestamo({ id }: { id: string }) {
  const { data, isPending, isError, error } = usePrestamo(id);
  if (isPending) return <Skeleton className="h-40" />;
  if (isError) return <p role="alert" className="text-texto-suave">{mensajeError(error, "No pudimos cargar el detalle.")}</p>;
  return (
    <div className="space-y-5">
      {data.condiciones && <p className="rounded-xl bg-fondo p-3 text-sm">Condiciones: {data.condiciones}</p>}
      <div>
        <h3 className="mb-2 font-extrabold text-morado">Cuotas</h3>
        <ul className="divide-y divide-lavanda/30">
          {data.cuotas.map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-2 py-2 text-sm">
              <span>n.º {c.numero} · {formatFechaCorta(c.fecha_vencimiento)}</span>
              <span className="cifras flex items-center gap-2">{formatCOP(c.saldo)} de {formatCOP(c.importe)} <Badge tono={TONO_CUOTA[c.estado]}>{ETIQUETA_ESTADO_CUOTA[c.estado]}</Badge></span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <h3 className="mb-2 font-extrabold text-morado">Historial de pagos</h3>
        {data.pagos.length === 0 ? <EstadoVacio titulo="Sin pagos todavía" texto="Cuando se pague una cuota aparecerá aquí." /> : (
          <ul className="divide-y divide-lavanda/30">
            {data.pagos.map((p) => (
              <li key={p.movimiento_id} className="flex items-center justify-between gap-2 py-2 text-sm">
                <span>Cuota {p.cuota_numero} · {formatFechaCorta(p.fecha)}</span>
                <span className="cifras flex items-center gap-2">{formatCOP(p.importe)} {p.estado_movimiento === "revertida" && <Badge>Revertido</Badge>}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}