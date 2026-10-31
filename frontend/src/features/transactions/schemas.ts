// frontend/src/features/transactions/schemas.ts
// Validación del formulario de movimientos y conversión al cuerpo que espera la API.

import { z } from "zod";
import { normalizarPesos } from "@/lib/pesos";
import type { NuevoMovimiento } from "./types";

/** Fecha de hoy en formato AAAA-MM-DD (hora local del dispositivo). */
export const hoy = (): string => new Date().toLocaleDateString("en-CA");

/** Reglas por tipo: ingreso necesita destino, gasto necesita origen y transferencia ambos, distintos. */
export const esquemaMovimiento = z
  .object({
    tipo: z.enum(["ingreso", "gasto", "transferencia"]),
    importe: z.string().refine((v) => /^[1-9]\d{0,11}$/.test(normalizarPesos(v)), "Escribe un importe en pesos enteros mayor que cero."),
    descripcion: z.string().trim().min(1, "Describe el movimiento.").max(500, "La descripción es demasiado larga."),
    fecha: z.string().refine((v) => v === "" || v <= hoy(), "La fecha no puede ser futura."),
    cuentaOrigenId: z.string(),
    cuentaDestinoId: z.string(),
    categoriaId: z.string(),
    pagadorId: z.string(),
  })
  .superRefine((d, ctx) => {
    const falta = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });
    if ((d.tipo === "gasto" || d.tipo === "transferencia") && !d.cuentaOrigenId) falta("cuentaOrigenId", "Elige la cuenta de la que sale el dinero.");
    if ((d.tipo === "ingreso" || d.tipo === "transferencia") && !d.cuentaDestinoId) falta("cuentaDestinoId", "Elige la cuenta a la que entra el dinero.");
    if (d.tipo === "transferencia" && d.cuentaOrigenId && d.cuentaOrigenId === d.cuentaDestinoId) {
      falta("cuentaDestinoId", "Las cuentas deben ser distintas.");
    }
  });

export type DatosMovimiento = z.infer<typeof esquemaMovimiento>;

/** Convierte el formulario en el cuerpo de la API, enviando solo los campos que aplican al tipo. */
export function aSolicitud(d: DatosMovimiento): NuevoMovimiento {
  return {
    tipo: d.tipo,
    importe: Number(normalizarPesos(d.importe)),
    descripcion: d.descripcion,
    fecha: d.fecha || undefined,
    cuenta_origen_id: d.tipo !== "ingreso" ? d.cuentaOrigenId : undefined,
    cuenta_destino_id: d.tipo !== "gasto" ? d.cuentaDestinoId : undefined,
    categoria_id: d.tipo !== "transferencia" && d.categoriaId ? d.categoriaId : undefined,
    pagador_id: d.tipo === "gasto" && d.pagadorId ? d.pagadorId : undefined,
  };
}

/** Reglas del motivo de reversión (mínimo 5 caracteres, igual que el backend). */
export const esquemaReversion = z.object({ motivo: z.string().trim().min(5, "Explica el motivo (mínimo 5 caracteres).").max(500, "El motivo es demasiado largo.") });
export type DatosReversion = z.infer<typeof esquemaReversion>;