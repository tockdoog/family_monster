// frontend/src/features/accounts/schemas.ts
// Validación del formulario de cuentas (el backend vuelve a validar todo).

import { z } from "zod";
import { normalizarPesos } from "@/lib/pesos";

export { normalizarPesos } from "@/lib/pesos";

/** Reglas: nombre, tipo, saldo inicial en pesos enteros (máx. 12 dígitos) y propietario si es fondo personal. */
export const esquemaCuenta = z
  .object({
    nombre: z.string().trim().min(1, "Escribe un nombre.").max(120, "El nombre es demasiado largo."),
    tipo: z.enum(["efectivo", "banco", "personal", "otra"], { message: "Elige un tipo de cuenta." }),
    saldoInicial: z
      .string()
      .refine((v) => /^\d{1,12}$/.test(normalizarPesos(v) || "0"), "Escribe solo pesos enteros, sin centavos ni comas."),
    propietarioId: z.string(),
  })
  // El backend exige propietario solo en cuentas personales.
  .superRefine((d, ctx) => {
    if (d.tipo === "personal" && !d.propietarioId) {
      ctx.addIssue({ code: "custom", path: ["propietarioId"], message: "Elige el integrante dueño del fondo." });
    }
  });

export type DatosCuenta = z.infer<typeof esquemaCuenta>;