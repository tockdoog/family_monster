// frontend/src/features/transactions/components/FiltrosMovimientos.tsx
// Filtros del listado: tipo, estado, cuenta y rango de fechas.

import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Cuenta } from "@/types/finanzas";
import { ETIQUETA_MOVIMIENTO, type FiltrosMovimientos } from "../types";

interface Props {
  valor: FiltrosMovimientos;
  cuentas: Cuenta[];
  onCambio: (f: FiltrosMovimientos) => void;
}

/** Controles de filtro; cada cambio notifica al padre, que reinicia la paginación. */
export function Filtros({ valor, cuentas, onCambio }: Props) {
  const cambiar = (campo: keyof FiltrosMovimientos) => (e: { target: { value: string } }) => onCambio({ ...valor, [campo]: e.target.value });
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <Select etiqueta="Tipo" value={valor.tipo} onChange={cambiar("tipo")}>
        <option value="">Todos</option>
        {Object.entries(ETIQUETA_MOVIMIENTO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </Select>
      <Select etiqueta="Estado" value={valor.estado} onChange={cambiar("estado")}>
        <option value="">Todos</option>
        <option value="confirmada">Confirmado</option>
        <option value="revertida">Revertido</option>
      </Select>
      <Select etiqueta="Cuenta" value={valor.cuentaId} onChange={cambiar("cuentaId")}>
        <option value="">Todas</option>
        {cuentas.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
      </Select>
      <Input etiqueta="Desde" type="date" value={valor.desde} onChange={cambiar("desde")} />
      <Input etiqueta="Hasta" type="date" value={valor.hasta} onChange={cambiar("hasta")} />
    </div>
  );
}