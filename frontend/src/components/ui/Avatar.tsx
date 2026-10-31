// frontend/src/components/ui/Avatar.tsx
// Avatar con las iniciales de la persona. El color es estable según el nombre (paleta morada).

import { cn } from "@/lib/cn";

// Combinaciones de fondo y texto con contraste suficiente.
const COLORES = ["bg-violeta text-blanco", "bg-morado-secundario text-blanco", "bg-morado text-blanco", "bg-lavanda text-morado-profundo"];

/** Círculo decorativo con iniciales (el nombre ya aparece como texto al lado). */
export function Avatar({ nombre, className }: { nombre: string; className?: string }) {
  const iniciales = nombre.trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
  const color = COLORES[[...nombre].reduce((a, c) => a + c.charCodeAt(0), 0) % COLORES.length];
  return (
    <span aria-hidden className={cn("grid size-11 shrink-0 place-items-center rounded-full font-extrabold", color, className)}>
      {iniciales}
    </span>
  );
}