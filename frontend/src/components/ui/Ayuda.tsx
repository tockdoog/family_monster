// frontend/src/components/ui/Ayuda.tsx
// Tooltip accesible: aparece al pasar el mouse o con el foco del teclado, y lo leen los lectores de pantalla.

import { Info } from "lucide-react";
import { useId } from "react";

/** Ícono de ayuda con una explicación breve de un concepto financiero. */
export function Ayuda({ texto }: { texto: string }) {
  const id = useId();
  return (
    <span className="group relative inline-flex">
      <button type="button" aria-describedby={id} aria-label="¿Qué significa?" className="rounded-full text-lavanda">
        <Info size={16} aria-hidden />
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute top-full left-1/2 z-10 mt-2 hidden w-56 -translate-x-1/2 rounded-lg bg-morado-profundo p-2 text-xs font-normal text-blanco group-focus-within:block group-hover:block"
      >
        {texto}
      </span>
    </span>
  );
}