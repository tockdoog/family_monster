// frontend/src/features/loans/components/PrestamoCard.tsx
// Tarjeta de un préstamo: partes, saldo, progreso y próxima cuota (todo calculado por el backend).

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { ETIQUETA_ESTADO_PRESTAMO, ETIQUETA_TIPO_PRESTAMO, type Prestamo } from "../types";

interface Props {
  prestamo: Prestamo;
  integrantes: Map<string, string>;
  puedePagar: boolean;
  onPagar: (p: Prestamo) => void;
  onDetalle: (p: Prestamo) => void;
}

/** Nombre de una parte: integrante, tercero o "El hogar". */
function parte(id: string | null, contraparte: string | null, integrantes: Map<string, string>): string {
  if (id) return integrantes.get(id) ?? "Integrante";
  return contraparte ?? "El hogar";
}

/** Muestra el préstamo; la barra es solo visual, el saldo es el oficial. */
export function PrestamoCard({ prestamo: p, integrantes, puedePagar, onPagar, onDetalle }: Props) {
  const total = Number(p.total_a_pagar);
  const porcentaje = total > 0 ? Math.min(100, Math.round((Number(p.pagado) / total) * 100)) : 0;
  const proxima = p.cuotas.find((c) => Number(c.saldo) > 0);
  // El hogar es la parte que no es integrante ni tercero.
  const presta = parte(p.prestamista_integrante_id, p.tipo === "al_hogar" ? p.contraparte_nombre : null, integrantes);
  const recibe = parte(p.prestatario_integrante_id, p.tipo === "del_hogar" ? p.contraparte_nombre : null, integrantes);

  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-extrabold text-morado">{presta} → {recibe}</h3>
          <p className="text-sm text-texto-suave">{ETIQUETA_TIPO_PRESTAMO[p.tipo]} · {formatFechaCorta(p.fecha)}</p>
        </div>
        <Badge tono={p.estado === "pagado" ? "exito" : "neutro"}>{ETIQUETA_ESTADO_PRESTAMO[p.estado]}</Badge>
      </div>
      <div role="progressbar" aria-valuenow={porcentaje} aria-valuemin={0} aria-valuemax={100} aria-label="Progreso del préstamo" className="mt-3 h-2.5 overflow-hidden rounded-full bg-lavanda/30">
        <div className="h-full rounded-full bg-violeta transition-[width] duration-700" style={{ width: `${porcentaje}%` }} />
      </div>
      <dl className="cifras mt-3 space-y-1 text-sm">
        <div className="flex justify-between"><dt className="text-texto-suave">Prestado</dt><dd className="font-semibold">{formatCOP(p.importe)}</dd></div>
        <div className="flex justify-between"><dt className="text-texto-suave">Total a devolver</dt><dd className="font-semibold">{formatCOP(p.total_a_pagar)}</dd></div>
        <div className="flex justify-between"><dt className="text-texto-suave">Falta por pagar</dt><dd className="font-extrabold text-morado">{formatCOP(p.saldo_pendiente)}</dd></div>
      </dl>
      {p.estado === "activo" && proxima && (
        <p className="mt-2 text-sm text-texto-suave">Próxima cuota: n.º {proxima.numero} · {formatFechaCorta(proxima.fecha_vencimiento)} · {formatCOP(proxima.saldo)}</p>
      )}
      <div className="mt-3 flex gap-2">
        {p.estado === "activo" && puedePagar && <Button onClick={() => onPagar(p)}>Pagar cuota</Button>}
        <Button variante="ghost" onClick={() => onDetalle(p)}>Ver detalle</Button>
      </div>
    </Card>
  );
}