// frontend/src/features/contributions/components/ListaReglas.tsx
// Reglas de reparto: cómo se divide cada gasto entre los integrantes (solo lectura).

import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import type { Regla } from "../types";

/** Texto de la parte de un integrante según su tipo. */
function textoParte(tipo: string, valor: string): string {
  if (tipo === "porcentaje") return `${Number(valor)} %`;
  if (tipo === "fijo") return `${formatCOP(valor)} fijos`;
  return "parte igual";
}

/** Lista de reglas con sus partes; "nombres" traduce ids de integrante a nombres. */
export function ListaReglas({ reglas, nombres }: { reglas: Regla[]; nombres: Map<string, string> }) {
  if (reglas.length === 0) {
    return <EstadoVacio titulo="Aún no hay reglas de reparto" texto="Sin una regla, los gastos no se dividen entre los integrantes y no hay aportes esperados." />;
  }
  return (
    <ul className="space-y-3">
      {reglas.map((r) => (
        <li key={r.id} className="rounded-xl bg-fondo p-3">
          <p className="font-semibold text-morado">{r.nombre}</p>
          <p className="text-sm text-texto-suave">
            Desde {formatFechaCorta(r.vigente_desde)}{r.vigente_hasta ? ` hasta ${formatFechaCorta(r.vigente_hasta)}` : " (vigente)"}
          </p>
          <p className="mt-1 text-sm">{r.items.map((it) => `${nombres.get(it.integrante_id) ?? "Integrante"}: ${textoParte(it.tipo, it.valor)}`).join(" · ")}</p>
        </li>
      ))}
    </ul>
  );
}