// frontend/src/types/paginacion.ts
// Respuesta paginada estándar del backend (shared/pagination.py → Pagina).

/** Página de resultados con el total para armar la paginación. */
export interface Pagina<T> {
  items: T[];
  total: number;
  limite: number;
  desplazamiento: number;
}