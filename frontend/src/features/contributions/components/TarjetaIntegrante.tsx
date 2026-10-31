// frontend/src/features/contributions/components/TarjetaIntegrante.tsx
// Estado de aportes de un integrante. Cifras y estado vienen del backend; el porcentaje es solo visual.

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { formatCOP } from "@/lib/formatCOP";
import type { ResumenIntegrante } from "@/types/finanzas";

interface Props {
  integrante: ResumenIntegrante;
  puedeReembolsar: boolean;
  onReembolsar: (i: ResumenIntegrante) => void;
}

/** Tarjeta con esperado, aportado, saldo y reembolso pendiente. */
export function TarjetaIntegrante({ integrante: i, puedeReembolsar, onReembolsar }: Props) {
  const esperado = Number(i.obligacion_esperada);
  const saldo = Number(i.saldo);
  const porcentaje = esperado > 0 ? Math.min(100, Math.round((Number(i.aportado_neto) / esperado) * 100)) : null;
  return (
    <Card>
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-extrabold text-morado">{i.nombre}</h3>
        <Badge tono={i.estado === "al_dia" ? "exito" : "aviso"}>{i.estado === "al_dia" ? "Al día" : "Pendiente"}</Badge>
      </div>
      {porcentaje !== null && (
        <div role="progressbar" aria-valuenow={porcentaje} aria-valuemin={0} aria-valuemax={100} aria-label={`Aportes de ${i.nombre}`}
          className="mt-3 h-2.5 overflow-hidden rounded-full bg-lavanda/30">
          <div className="h-full rounded-full bg-violeta transition-[width] duration-700" style={{ width: `${porcentaje}%` }} />
        </div>
      )}
      <dl className="cifras mt-3 space-y-1 text-sm">
        <div className="flex justify-between"><dt className="text-texto-suave">Le correspondía</dt><dd className="font-semibold">{formatCOP(i.obligacion_esperada)}</dd></div>
        <div className="flex justify-between"><dt className="text-texto-suave">Ha puesto</dt><dd className="font-semibold">{formatCOP(i.aportado_neto)}</dd></div>
        <div className="flex justify-between">
          <dt className="text-texto-suave">{saldo >= 0 ? "Saldo a favor" : "Le falta aportar"}</dt>
          <dd className="font-semibold">{formatCOP(Math.abs(saldo))}</dd>
        </div>
      </dl>
      {Number(i.reembolso_pendiente) > 0 && (
        <div className="mt-3 rounded-xl bg-aviso/15 p-3 text-sm">
          <p>El hogar le debe {formatCOP(i.reembolso_pendiente)} por gastos pagados con su dinero.</p>
          {puedeReembolsar && <Button variante="outline" className="mt-2" onClick={() => onReembolsar(i)}>Reembolsar</Button>}
        </div>
      )}
    </Card>
  );
}