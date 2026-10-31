// frontend/src/features/categories/schemas.ts
// Validación del nombre de categoría (1 a 60 caracteres, igual que el backend).

import { z } from "zod";

export const esquemaCategoria = z.object({ nombre: z.string().trim().min(1, "Escribe un nombre.").max(60, "Máximo 60 caracteres.") });
export type DatosCategoria = z.infer<typeof esquemaCategoria>;