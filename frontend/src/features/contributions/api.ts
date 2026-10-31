// frontend/src/features/contributions/api.ts
// Resumen, reglas, aportes y reembolsos contra /contributions y /contribution-rules.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Movimiento } from "@/features/transactions/types";
import type { Regla, ResumenAportes, SolicitudFondos } from "./types";

/** Aportes esperados y reales del mes actual (el backend calcula todo). */
export function useResumenAportes() {
  return useQuery({ queryKey: ["aportes"], queryFn: ({ signal }) => api.get<ResumenAportes>("/contributions/summary", signal) });
}

/** Reglas de reparto vigentes e históricas. */
export function useReglas() {
  return useQuery({ queryKey: ["reglas"], queryFn: ({ signal }) => api.get<Regla[]>("/contribution-rules", signal) });
}

/** Registra un aporte o un reembolso y refresca todo lo que depende de saldos. */
export function useRegistrarFondos(modo: "aporte" | "reembolso") {
  const cliente = useQueryClient();
  const ruta = modo === "aporte" ? "/contributions" : "/contributions/reimbursements";
  return useMutation({
    mutationFn: ({ datos, clave }: { datos: SolicitudFondos; clave: string }) => api.post<Movimiento>(ruta, datos, clave),
    onSuccess: () => {
      for (const k of ["aportes", "movimientos", "cuentas", "tablero"]) void cliente.invalidateQueries({ queryKey: [k] });
    },
  });
}