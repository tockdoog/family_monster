// frontend/src/features/members/schemas.ts
// Validación de formularios de integrantes. La contraseña replica la política del backend (security.py).

import { z } from "zod";

/** Alta de integrante. */
export const esquemaIntegrante = z.object({ nombre: z.string().trim().min(1, "Escribe el nombre.").max(120, "El nombre es demasiado largo.") });
export type DatosIntegrante = z.infer<typeof esquemaIntegrante>;

/** Acceso: correo, contraseña (12 a 128 caracteres, con letra y número) y rol. */
export const esquemaAcceso = z.object({
  email: z.string().trim().min(1, "Escribe el correo.").email("Escribe un correo válido."),
  contrasena: z
    .string()
    .min(12, "Debe tener al menos 12 caracteres.")
    .max(128, "No puede superar 128 caracteres.")
    .regex(/[A-Za-zÁÉÍÓÚáéíóúÑñ]/, "Debe incluir al menos una letra.")
    .regex(/\d/, "Debe incluir al menos un número."),
  rol: z.enum(["miembro", "admin"]),
});
export type DatosAcceso = z.infer<typeof esquemaAcceso>;