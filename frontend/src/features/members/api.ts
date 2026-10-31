// frontend/src/features/members/api.ts
// Integrantes del hogar: consulta, alta y acceso a la aplicación (/members).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Integrante, NuevoAcceso } from "./types";

/** Lista los integrantes; se reutiliza en cuentas, aportes, movimientos y préstamos. */
export function useIntegrantes() {
  return useQuery({ queryKey: ["integrantes"], queryFn: ({ signal }) => api.get<Integrante[]>("/members", signal) });
}

/** Registra un integrante (sin acceso a la app todavía). */
export function useCrearIntegrante() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (nombre: string) => api.post<Integrante>("/members", { nombre }),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["integrantes"] }),
  });
}

/** Crea las credenciales de un integrante existente. */
export function useOtorgarAcceso() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: NuevoAcceso }) => api.post<Integrante>(`/members/${id}/acceso`, datos),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ["integrantes"] }),
  });
}