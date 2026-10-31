// frontend/src/types/api.ts
// Tipos de la sesión según backend/app/modules/auth/schemas.py (SesionSalida).

/** Usuario autenticado (el backend nunca envía el hash). */
export interface Usuario {
  id: string;
  email: string;
  nombre_completo: string;
}

/** Identificación mínima del hogar. */
export interface HogarResumen {
  id: string;
  nombre: string;
}

/** Sesión: usuario, hogar, rol y permisos (solo informativos; el backend valida cada petición). */
export interface Sesion {
  usuario: Usuario;
  hogar: HogarResumen;
  rol: string;
  permisos: string[];
}