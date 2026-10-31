// frontend/src/features/transactions/api.ts
// Listado, registro y reversión de movimientos. Las operaciones que mueven dinero envían Idempotency-Key.

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Pagina } from "@/types/paginacion";
import type { FiltrosMovimientos, Movimiento, NuevoMovimiento } from "./types";

/** Cantidad de movimientos por página. */
export const LIMITE = 20;

/** Lista movimientos con filtros y paginación (el backend los ordena del más reciente al más antiguo). */
export function useMovimientos(f: FiltrosMovimientos, desplazamiento: number) {
  const q = new URLSearchParams({ limite: String(LIMITE), desplazamiento: String(desplazamiento) });
  if (f.tipo) q.set("tipo", f.tipo);
  if (f.estado) q.set("estado", f.estado);
  if (f.cuentaId) q.set("cuenta_id", f.cuentaId);
  if (f.desde) q.set("desde", f.desde);
  if (f.hasta) q.set("hasta", f.hasta);
  return useQuery({
    queryKey: ["movimientos", f, desplazamiento],
    queryFn: ({ signal }) => api.get<Pagina<Movimiento>>(`/transactions?${q.toString()}`, signal),
    placeholderData: keepPreviousData,
  });
}

// Un movimiento cambia saldos: se refrescan listado, cuentas y panel.
function refrescar(cliente: QueryClient) {
  for (const clave of ["movimientos", "cuentas", "tablero"]) void cliente.invalidateQueries({ queryKey: [clave] });
}

/** Registra un ingreso, gasto o transferencia. */
export function useRegistrarMovimiento() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ datos, clave }: { datos: NuevoMovimiento; clave: string }) => api.post<Movimiento>("/transactions", datos, clave),
    onSuccess: () => refrescar(cliente),
  });
}

/** Revierte un movimiento con un motivo obligatorio. */
export function useRevertirMovimiento() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motivo, clave }: { id: string; motivo: string; clave: string }) =>
      api.post<Movimiento>(`/transactions/${id}/reverse`, { motivo }, clave),
    onSuccess: () => refrescar(cliente),
  });
}