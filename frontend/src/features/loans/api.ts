// frontend/src/features/loans/api.ts
// Listado, detalle, alta y pago de cuotas contra /loans.

import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { api } from "@/services/api/client";
import type { Pagina } from "@/types/paginacion";
import type { NuevoPagoCuota, NuevoPrestamo, Prestamo, PrestamoDetalle } from "./types";

/** Préstamos por página. */
export const LIMITE = 20;

/** Lista préstamos con filtro opcional por estado. */
export function usePrestamos(estado: string, desplazamiento: number) {
  const q = new URLSearchParams({ limite: String(LIMITE), desplazamiento: String(desplazamiento) });
  if (estado) q.set("estado", estado);
  return useQuery({
    queryKey: ["prestamos", estado, desplazamiento],
    queryFn: ({ signal }) => api.get<Pagina<Prestamo>>(`/loans?${q.toString()}`, signal),
    placeholderData: keepPreviousData,
  });
}

/** Detalle con cuotas e historial de pagos. */
export function usePrestamo(id: string) {
  return useQuery({ queryKey: ["prestamo", id], queryFn: ({ signal }) => api.get<PrestamoDetalle>(`/loans/${id}`, signal) });
}

// Crear un préstamo o pagar una cuota mueve dinero: se refrescan todas las vistas que lo muestran.
function refrescar(cliente: QueryClient) {
  for (const k of ["prestamos", "prestamo", "movimientos", "cuentas", "tablero"]) void cliente.invalidateQueries({ queryKey: [k] });
}

/** Crea el préstamo, sus cuotas y su desembolso (Idempotency-Key obligatoria en el backend). */
export function useCrearPrestamo() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ datos, clave }: { datos: NuevoPrestamo; clave: string }) => api.post<Prestamo>("/loans", datos, clave),
    onSuccess: () => refrescar(cliente),
  });
}

/** Paga una cuota (total o parcial). */
export function usePagarCuota() {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos, clave }: { id: string; datos: NuevoPagoCuota; clave: string }) => api.post<unknown>(`/loans/${id}/payments`, datos, clave),
    onSuccess: () => refrescar(cliente),
  });
}