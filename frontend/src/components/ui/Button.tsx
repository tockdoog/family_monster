// frontend/src/components/ui/Button.tsx
// Botón del sistema de diseño: variantes, estado de carga y objetivo táctil de 44 px.

import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Variantes visuales disponibles.
type Variante = "primary" | "secondary" | "outline" | "ghost" | "danger";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  cargando?: boolean;
}

// Clases por variante (todas usan tokens de theme.css).
const ESTILOS: Record<Variante, string> = {
  primary: "bg-violeta text-blanco hover:bg-morado-secundario",
  secondary: "bg-morado text-blanco hover:bg-morado-profundo",
  outline: "border-2 border-violeta text-violeta hover:bg-fondo",
  ghost: "text-morado-secundario hover:bg-fondo",
  danger: "bg-alerta text-blanco hover:opacity-90",
};

/** Botón con foco visible; se bloquea mientras carga para evitar envíos dobles. */
export function Button({ variante = "primary", cargando = false, className, disabled, children, ...resto }: Props) {
  return (
    <button
      {...resto}
      disabled={disabled || cargando}
      aria-busy={cargando}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 font-semibold transition duration-150 enabled:active:scale-[0.97]",
        "disabled:cursor-not-allowed disabled:opacity-60",
        ESTILOS[variante],
        className,
      )}
    >
      {cargando ? "Procesando…" : children}
    </button>
  );
}