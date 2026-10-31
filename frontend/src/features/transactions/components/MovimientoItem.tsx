// frontend/src/features/transactions/components/MovimientoItem.tsx
// Un movimiento: tarjeta apilada en móvil y fila amplia en pantallas grandes.

import { Undo2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { ETIQUETA_MOVIMIENTO, type Movimiento } from "../types";

interface Props {
  movimiento: Movimiento;
  cuentas: Map<string, string>;
  categorias: Map<string, string>;
  integrantes: Map<string, string>;
  puedeRevertir: boolean;
  onRevertir: (m: Movimiento) => void;
}

/** Muestra el movimiento con sus efectos por cuenta (+ entra, − sale). */
export function MovimientoItem({ movimiento: m, cuentas, categorias, integrantes, puedeRevertir, onRevertir }: Props) {
  const revertible = puedeRevertir && m.estado === "confirmada" && m.tipo !== "reversion";
  const detalle = [
    m.categoria_id && categorias.get(m.categoria_id),
    m.pagador_id && `Pagó ${integrantes.get(m.pagador_id) ?? "un integrante"}`,
    m.motivo && `Motivo: ${m.motivo}`,
  ].filter(Boolean).join(" · ");

  return (
    <li className="flex flex-col gap-2 rounded-tarjeta bg-blanco p-4 shadow-tarjeta md:flex-row md:items-center md:justify-between">
      <div className="min-w-0">
        <p className="font-semibold text-texto">{m.descripcion}</p>
        <p className="text-sm text-texto-suave">{formatFechaCorta(m.fecha)}{detalle && ` · ${detalle}`}</p>
        <p className="cifras text-sm text-texto-suave">
          {m.lineas.map((l) => `${cuentas.get(l.cuenta_id) ?? "Cuenta"}: ${Number(l.importe) > 0 ? "+" : ""}${formatCOP(l.importe)}`).join(" · ")}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        <Badge>{ETIQUETA_MOVIMIENTO[m.tipo] ?? m.tipo}</Badge>
        <Badge tono={m.estado === "confirmada" ? "exito" : "neutro"}>{m.estado === "confirmada" ? "Confirmado" : "Revertido"}</Badge>
        <p className="cifras text-lg font-extrabold text-morado">{formatCOP(m.importe)}</p>
        {revertible && (
          <Button variante="ghost" onClick={() => onRevertir(m)} aria-label={`Revertir ${m.descripcion}`}>
            <Undo2 size={18} aria-hidden /> Revertir
          </Button>
        )}
      </div>
    </li>
  );
}