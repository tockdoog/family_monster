// frontend/src/features/accounts/api.ts
// Consultas y creación de cuentas contra /accounts.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Cuenta } from "@/types/finanzas";

/** Cuerpo de POST /accounts para cuentas de fondo común (las personales llegan con el módulo de integrantes). */
export interface NuevaCuenta {
  nombre: string;
  tipo: "efectivo" | "banco" | "otra";
  saldo_inicial: number;
}

/** Lista las cuentas con el saldo calculado por el backend. */
export function useCuentas() {
  return useQuery({ queryKey: ["cuentas"], queryFn: ({ signal }) => api.get<Cuenta[]>("/accounts", signal) });
}

/** Crea una cuenta y refresca el listado y el panel principal. */
export function useCrearCuenta() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (datos: NuevaCuenta) => api.post<Cuenta>("/accounts", datos),
    onSuccess: () => {
      void cliente.invalidateQueries({ queryKey: ["cuentas"] });
      void cliente.invalidateQueries({ queryKey: ["tablero"] });
    },
  });
}