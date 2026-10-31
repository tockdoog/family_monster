// frontend/src/features/accounts/components/CuentaCard.tsx
// Tarjeta de una cuenta: nombre, tipo, responsable, estado y saldos (calculados por el backend).

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatCOP } from "@/lib/formatCOP";
import type { Cuenta } from "@/types/finanzas";
import { ETIQUETA_TIPO } from "../types";

/** Muestra una cuenta; "propietario" es el nombre del dueño si es un fondo personal. */
export function CuentaCard({ cuenta, propietario }: { cuenta: Cuenta; propietario?: string }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-extrabold text-morado">{cuenta.nombre}</h3>
          <p className="text-sm text-texto-suave">
            {ETIQUETA_TIPO[cuenta.tipo] ?? cuenta.tipo}
            {propietario && ` · ${propietario}`}
          </p>
        </div>
        <Badge tono={cuenta.activa ? "exito" : "neutro"}>{cuenta.activa ? "Activa" : "Inactiva"}</Badge>
      </div>
      <p className="cifras mt-3 text-2xl font-extrabold text-morado">{formatCOP(cuenta.saldo_actual)}</p>
      <p className="text-sm text-texto-suave">Saldo actual · inició con {formatCOP(cuenta.saldo_inicial)}</p>
    </Card>
  );
}