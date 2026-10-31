// frontend/src/components/ui/PasoConfirmacion.tsx
// Segundo paso de las operaciones con dinero: resumen claro y confirmación explícita.

import { Button } from "./Button";

interface Props {
  texto: string;
  filas: Array<[string, string]>;
  cargando: boolean;
  etiqueta?: string;
  onVolver: () => void;
  onConfirmar: () => void;
}

/** Muestra lo que se va a registrar y pide confirmar antes de enviarlo. */
export function PasoConfirmacion({ texto, filas, cargando, etiqueta = "Confirmar y registrar", onVolver, onConfirmar }: Props) {
  return (
    <div className="space-y-4">
      <p className="text-texto-suave">{texto}</p>
      <dl className="space-y-1 rounded-xl bg-fondo p-4">
        {filas.map(([k, v]) => (
          <div key={k}><dt className="inline font-semibold">{k}: </dt><dd className="cifras inline">{v}</dd></div>
        ))}
      </dl>
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" disabled={cargando} onClick={onVolver}>Volver</Button>
        <Button type="button" className="flex-1" cargando={cargando} onClick={onConfirmar}>{etiqueta}</Button>
      </div>
    </div>
  );
}