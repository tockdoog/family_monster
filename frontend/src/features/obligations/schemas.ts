// frontend/src/features/obligations/schemas.ts
// Validación de los formularios de obligaciones (el backend vuelve a validar todo).

import { z } from "zod";
import { hoy } from "@/features/transactions/schemas";
import { MENSAJE_IMPORTE, esImportePositivo } from "@/lib/pesos";

/** Alta de obligación: factura, servicio o deuda. */
export const esquemaObligacion = z.object({
  descripcion: z.string().trim().min(1, "Describe la obligación.").max(300, "La descripción es demasiado larga."),
  categoriaId: z.string().min(1, "Elige una categoría."),
  importe: z.string().refine(esImportePositivo, MENSAJE_IMPORTE),
  fechaVencimiento: z.string().min(1, "Elige la fecha de vencimiento."),
  acreedor: z.string().trim().min(1, "¿A quién se le debe?").max(120, "El nombre es demasiado largo."),
  responsableId: z.string(),
});
export type DatosObligacion = z.infer<typeof esquemaObligacion>;

/** Pago total o parcial desde una cuenta. */
export const esquemaPago = z.object({
  importe: z.string().refine(esImportePositivo, MENSAJE_IMPORTE),
  cuentaOrigenId: z.string().min(1, "Elige la cuenta con la que se paga."),
  fecha: z.string().refine((v) => v === "" || v <= hoy(), "La fecha no puede ser futura."),
  descripcion: z.string().trim().max(500, "La nota es demasiado larga."),
});
export type DatosPago = z.infer<typeof esquemaPago>;

/** Motivo obligatorio para anular (mínimo 5 caracteres, igual que el backend). */
export const esquemaMotivo = z.object({ motivo: z.string().trim().min(5, "Explica el motivo (mínimo 5 caracteres).").max(500, "El motivo es demasiado largo.") });
export type DatosMotivo = z.infer<typeof esquemaMotivo>;