// frontend/src/lib/cn.ts
// Une clases CSS ignorando valores vacíos (evita una dependencia solo para esto).

/** Devuelve las clases válidas separadas por espacio. */
export function cn(...clases: Array<string | false | null | undefined>): string {
  return clases.filter(Boolean).join(" ");
}