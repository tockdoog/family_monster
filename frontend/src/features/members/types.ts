// frontend/src/features/members/types.ts
// Tipo del integrante según members/schemas.py → IntegranteSalida.

/** Integrante del hogar; "rol" es null si no tiene acceso a la aplicación. */
export interface Integrante {
  id: string;
  nombre: string;
  activo: boolean;
  tiene_acceso: boolean;
  rol: string | null;
}