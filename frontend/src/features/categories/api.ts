// frontend/src/features/categories/api.ts
// Categorías del hogar: consulta, alta y cambios (/categories). Nunca se borran: se desactivan.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";

/** Categoría según categories/schemas.py → CategoriaSalida. */
export interface Categoria {
  id: string;
  nombre: string;
  activa: boolean;
}

/** Lista las categorías; se reutiliza en movimientos y obligaciones. */
export function useCategorias() {
  return useQuery({ queryKey: ["categorias"], queryFn: ({ signal }) => api.get<Categoria[]>("/categories", signal) });
}

/** Crea una categoría. */
export function useCrearCategoria() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => api.post<Categoria>("/categories", { nombre }),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["categorias"] }),
  });
}

/** Renombra o activa/desactiva una categoría (al menos un cambio). */
export function useActualizarCategoria() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, cambios }: { id: string; cambios: { nombre?: string; activa?: boolean } }) => api.patch<Categoria>(`/categories/${id}`, cambios),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["categorias"] }),
  });
}