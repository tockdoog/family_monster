// frontend/src/features/obligations/api.ts
// Listado, alta, pago y anulación de obligaciones contra /obligations.

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Pagina } from "@/types/paginacion";
import type { NuevaObligacion, NuevoPago, Obligacion } from "./types";

/** Obligaciones por página. */
export const LIMITE = 20;

/** Lista obligaciones por fecha de vencimiento, con filtro opcional por estado. */
export function useObligaciones(estado: string, desplazamiento: number) {
  const q = new URLSearchParams({ limite: String(LIMITE), desplazamiento: String(desplazamiento) });
  if (estado) q.set("estado", estado);
  return useQuery({
    queryKey: ["obligaciones", estado, desplazamiento],
    queryFn: ({ signal }) => api.get<Pagina<Obligacion>>(`/obligations?${q.toString()}`, signal),
    placeholderData: keepPreviousData,
  });
}

// Pagar o anular cambia saldos y vencimientos: se refrescan las pantallas que los muestran.
function refrescar(cliente: QueryClient) {
  for (const k of ["obligaciones", "movimientos", "cuentas", "tablero"]) void cliente.invalidateQueries({ queryKey: [k] });
}

/** Registra una obligación. */
export function useCrearObligacion() {
  const cliente = useQueryClient();
  return useMutation({ mutationFn: (datos: NuevaObligacion) => api.post<Obligacion>("/obligations", datos), onSuccess: () => refrescar(cliente) });
}

/** Paga una obligación (total o parcial) con Idempotency-Key. */
export function usePagarObligacion() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos, clave }: { id: string; datos: NuevoPago; clave: string }) =>
      api.post<{ obligacion: Obligacion }>(`/obligations/${id}/payments`, datos, clave),
    onSuccess: () => refrescar(cliente),
  });
}

/** Anula una obligación sin pagos. */
export function useAnularObligacion() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motivo }: { id: string; motivo: string }) => api.post<Obligacion>(`/obligations/${id}/cancel`, { motivo }),
    onSuccess: () => refrescar(cliente),
  });
}