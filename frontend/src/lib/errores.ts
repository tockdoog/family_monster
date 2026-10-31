// frontend/src/lib/errores.ts
// Convierte cualquier error en un mensaje legible para el usuario.

import { ErrorApi } from "@/services/api/client";

/** Devuelve el mensaje del backend si existe; si no, el texto por defecto indicado. */
export function mensajeError(error: unknown, porDefecto: string): string {
  return error instanceof ErrorApi ? error.message : porDefecto;
}