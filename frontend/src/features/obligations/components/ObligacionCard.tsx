// frontend/src/features/obligations/components/ObligacionCard.tsx
// Tarjeta de una obligación: acreedor, vencimiento, saldo y acciones según estado y permisos.

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { ETIQUETA_ESTADO, TONO_ESTADO, type Obligacion } from "../types";

interface Props {
  obligacion: Obligacion;
  categorias: Map<string, string>;
  integrantes: Map<string, string>;
  puedePagar: boolean;
  puedeGestionar: boolean;
  onPagar: (o: Obligacion) => void;
  onAnular: (o: Obligacion) => void;
}

/** Muestra la obligación; los montos y el estado son los del backend (la barra es solo visual). */
export function ObligacionCard({ obligacion: o, categorias, integrantes, puedePagar, puedeGestionar, onPagar, onAnular }: Props) {
  const original = Number(o.importe_original);
  const porcentaje = original > 0 ? Math.min(100, Math.round((Number(o.pagado) / original) * 100)) : 0;
  const abierta = o.estado === "pendiente" || o.estado === "parcialmente_pagada" || o.estado === "vencida";
  const anulable = puedeGestionar && o.estado !== "anulada" && o.estado !== "pagada" && Number(o.pagado) === 0;
  const meta = [categorias.get(o.categoria_id), o.responsable_id && `Responsable: ${integrantes.get(o.responsable_id) ?? "—"}`].filter(Boolean).join(" · ");

  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-extrabold text-morado">{o.descripcion}</h3>
          <p className="text-sm text-texto-suave">{o.acreedor} · vence el {formatFechaCorta(o.fecha_vencimiento)}</p>
          {meta && <p className="text-sm text-texto-suave">{meta}</p>}
        </div>
        <Badge tono={TONO_ESTADO[o.estado]}>{ETIQUETA_ESTADO[o.estado]}</Badge>
      </div>
      <div role="progressbar" aria-valuenow={porcentaje} aria-valuemin={0} aria-valuemax={100} aria-label={`Pagado de ${o.descripcion}`}
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-lavanda/30">
        <div className="h-full rounded-full bg-violeta transition-[width] duration-700" style={{ width: `${porcentaje}%` }} />
      </div>
      <dl className="cifras mt-3 space-y-1 text-sm">
        <div className="flex justify-between"><dt className="text-texto-suave">Valor total</dt><dd className="font-semibold">{formatCOP(o.importe_original)}</dd></div>
        <div className="flex justify-between"><dt className="text-texto-suave">Pagado</dt><dd className="font-semibold">{formatCOP(o.pagado)}</dd></div>
        <div className="flex justify-between"><dt className="text-texto-suave">Falta por pagar</dt><dd className="font-extrabold text-morado">{formatCOP(o.saldo_pendiente)}</dd></div>
      </dl>
      {o.motivo_anulacion && <p className="mt-2 text-sm text-texto-suave">Motivo de anulación: {o.motivo_anulacion}</p>}
      {((abierta && puedePagar) || anulable) && (
        <div className="mt-3 flex gap-2">
          {abierta && puedePagar && <Button onClick={() => onPagar(o)}>Pagar</Button>}
          {anulable && <Button variante="ghost" onClick={() => onAnular(o)}>Anular</Button>}
        </div>
      )}
    </Card>
  );
}