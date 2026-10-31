// frontend/src/features/contributions/schemas.ts
// Validación del formulario de aportes y reembolsos.

import { z } from "zod";
import { MENSAJE_IMPORTE, esImportePositivo, normalizarPesos } from "@/lib/pesos";
import { hoy } from "@/features/transactions/schemas";
import type { SolicitudFondos } from "./types";

export type ModoFondos = "aporte" | "reembolso";

const base = z.object({
  integranteId: z.string().min(1, "Elige un integrante."),
  importe: z.string().refine(esImportePositivo, MENSAJE_IMPORTE),
  cuentaOrigenId: z.string(),
  cuentaDestinoId: z.string(),
  fecha: z.string().refine((v) => v === "" || v <= hoy(), "La fecha no puede ser futura."),
  descripcion: z.string().trim().max(500, "La descripción es demasiado larga."),
});

export type DatosFondos = z.infer<typeof base>;

/** Aporte: entra a un fondo común. Reembolso: sale del fondo común hacia la cuenta personal del integrante. */
export const esquemaFondos = (modo: ModoFondos) =>
  base.superRefine((d, ctx) => {
    const falta = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });
    if (modo === "aporte" && !d.cuentaDestinoId) falta("cuentaDestinoId", "Elige el fondo común que recibe el dinero.");
    if (modo === "reembolso" && !d.cuentaOrigenId) falta("cuentaOrigenId", "Elige el fondo común que devuelve el dinero.");
    if (modo === "reembolso" && !d.cuentaDestinoId) falta("cuentaDestinoId", "Elige la cuenta personal que recibe el dinero.");
  });

/** Convierte el formulario en el cuerpo de la API. */
export function aSolicitudFondos(d: DatosFondos): SolicitudFondos {
  return {
    integrante_id: d.integranteId,
    importe: Number(normalizarPesos(d.importe)),
    cuenta_origen_id: d.cuentaOrigenId || undefined,
    cuenta_destino_id: d.cuentaDestinoId || undefined,
    fecha: d.fecha || undefined,
    descripcion: d.descripcion || undefined,
  };
}