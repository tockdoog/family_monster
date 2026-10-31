// frontend/src/features/auth/schemas.ts
// Validación del formulario de ingreso (el backend vuelve a validar todo).

import { z } from "zod";

/** Reglas del login: correo válido y contraseña presente (máximo 128, igual que el backend). */
export const esquemaLogin = z.object({
  email: z.string().trim().min(1, "Escribe tu correo.").email("Escribe un correo válido."),
  contrasena: z.string().min(1, "Escribe tu contraseña.").max(128, "La contraseña es demasiado larga."),
});

export type DatosLogin = z.infer<typeof esquemaLogin>;