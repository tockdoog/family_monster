// frontend/src/features/members/api.ts
// Consulta de integrantes del hogar (GET /members).

import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Integrante } from "./types";

/** Lista los integrantes; se reutiliza en cuentas, aportes y movimientos. */
export function useIntegrantes() {
  return useQuery({ queryKey: ["integrantes"], queryFn: ({ signal }) => api.get<Integrante[]>("/members", signal) });
}