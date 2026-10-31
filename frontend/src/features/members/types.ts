// frontend/src/features/members/types.ts
// Tipos de integrantes según members/schemas.py.

/** Integrante del hogar; "rol" es null si no tiene acceso a la aplicación. */
export interface Integrante {
  id: string;
  nombre: string;
  activo: boolean;
  tiene_acceso: boolean;
  rol: string | null;
}

/** Cuerpo de POST /members/{id}/acceso. */
export interface NuevoAcceso {
  email: string;
  contrasena: string;
  rol: "admin" | "miembro";
}

/** Nombre en español de cada rol. */
export const ETIQUETA_ROL: Record<string, string> = { admin: "Administrador", miembro: "Miembro" };