// frontend/src/features/dashboard/components/PanelCuentas.tsx
// Lista de cuentas activas con su saldo actual (calculado por el backend).

import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { formatCOP } from "@/lib/formatCOP";
import type { Cuenta } from "@/types/finanzas";

/** Cuentas del hogar: fondo común y personales. */
export function PanelCuentas({ cuentas }: { cuentas: Cuenta[] }) {
  const activas = cuentas.filter((c) => c.activa);
  if (activas.length === 0) {
    return <EstadoVacio titulo="Sin cuentas" texto="Crea una cuenta de efectivo o banco para empezar a registrar movimientos." />;
  }
  return (
    <ul className="divide-y divide-lavanda/30">
      {activas.map((c) => (
        <li key={c.id} className="flex items-center justify-between gap-3 py-3">
          <div>
            <p className="font-semibold text-texto">{c.nombre}</p>
            <p className="text-sm text-texto-suave">{c.es_fondo_comun ? "Fondo común" : "Fondo personal"}</p>
          </div>
          <p className="cifras font-bold text-morado">{formatCOP(c.saldo_actual)}</p>
        </li>
      ))}
    </ul>
  );
}