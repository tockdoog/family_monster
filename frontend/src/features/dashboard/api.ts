// frontend/src/features/dashboard/api.ts
// Consulta del panel principal. Sin fechas, el backend usa el mes actual.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Tablero } from "./types";

/** Carga el tablero del hogar (cache y estados de carga/error gestionados por TanStack Query). */
export function useTablero() {
  return useQuery({
    queryKey: ["tablero"],
    queryFn: ({ signal }) => api.get<Tablero>("/dashboard/summary", signal),
  });
}