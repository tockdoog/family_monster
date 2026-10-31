// frontend/src/components/ui/Input.tsx
// Campo de texto accesible: etiqueta asociada, mensaje de error anunciado y acción opcional (ej. mostrar contraseña).

import { useId, type ComponentPropsWithRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface Props extends ComponentPropsWithRef<"input"> {
  etiqueta: string;
  error?: string;
  accion?: ReactNode;
}

/** Input con etiqueta visible, estado de error y foco claro. */
export function Input({ etiqueta, error, accion, className, id, ...resto }: Props) {
  const idAuto = useId();
  const idCampo = id ?? idAuto;
  const idError = `${idCampo}-error`;
  return (
    <div>
      <label htmlFor={idCampo} className="text-sm font-semibold text-morado">
        {etiqueta}
      </label>
      <div className="relative mt-1">
        <input
          {...resto}
          id={idCampo}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? idError : undefined}
          className={cn(
            "min-h-11 w-full rounded-xl border-2 bg-blanco px-4 text-texto placeholder:text-texto-suave",
            error ? "border-alerta" : "border-lavanda/60",
            accion && "pr-12",
            className,
          )}
        />
        {accion && <div className="absolute inset-y-0 right-1 flex items-center">{accion}</div>}
      </div>
      {error && (
        <p id={idError} role="alert" className="mt-1 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}