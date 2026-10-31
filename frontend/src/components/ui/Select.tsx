// frontend/src/components/ui/Select.tsx
// Selector accesible con etiqueta visible y mensaje de error anunciado.

import { useId, type ComponentPropsWithRef } from "react";
import { cn } from "@/lib/cn";

interface Props extends ComponentPropsWithRef<"select"> {
  etiqueta: string;
  error?: string;
}

/** Lista desplegable con el mismo estilo que Input. */
export function Select({ etiqueta, error, className, id, children, ...resto }: Props) {
  const idAuto = useId();
  const idCampo = id ?? idAuto;
  const idError = `${idCampo}-error`;
  return (
    <div>
      <label htmlFor={idCampo} className="text-sm font-semibold text-morado">
        {etiqueta}
      </label>
      <select
        {...resto}
        id={idCampo}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? idError : undefined}
        className={cn("mt-1 min-h-11 w-full rounded-xl border-2 bg-blanco px-3 text-texto", error ? "border-alerta" : "border-lavanda/60", className)}
      >
        {children}
      </select>
      {error && (
        <p id={idError} role="alert" className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}