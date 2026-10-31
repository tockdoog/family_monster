// frontend/src/features/members/components/IntegranteCard.tsx
// Tarjeta de un integrante: avatar, estado y acceso a la aplicación.

import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ETIQUETA_ROL, type Integrante } from "../types";

/** Muestra al integrante; "Dar acceso" solo aparece si hay permiso y aún no tiene acceso. */
export function IntegranteCard({ integrante: i, puedeGestionar, onAcceso }: { integrante: Integrante; puedeGestionar: boolean; onAcceso: (i: Integrante) => void }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <Avatar nombre={i.nombre} />
        <div className="min-w-0">
          <h3 className="truncate font-extrabold text-morado">{i.nombre}</h3>
          <p className="text-sm text-texto-suave">{i.tiene_acceso ? `Con acceso · ${ETIQUETA_ROL[i.rol ?? ""] ?? i.rol}` : "Sin acceso a la aplicación"}</p>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <Badge tono={i.activo ? "exito" : "neutro"}>{i.activo ? "Activo" : "Inactivo"}</Badge>
        {puedeGestionar && i.activo && !i.tiene_acceso && <Button variante="outline" onClick={() => onAcceso(i)}>Dar acceso</Button>}
      </div>
    </Card>
  );
}