// frontend/src/features/reports/api.ts
// Informe mensual, evolución de meses y exportación a CSV.

import { useQueries, useQuery } from "@tanstack/react-query";
import type { Tablero } from "@/features/dashboard/types";
import { api } from "@/services/api/client";
import { limitesDeMes } from "./meses";
import type { InformeMensual } from "./types";

/** Informe de un mes (GET /reports/monthly). */
export function useInformeMensual(mes: string) {
  return useQuery({ queryKey: ["informe", mes], queryFn: ({ signal }) => api.get<InformeMensual>(`/reports/monthly?mes=${mes}`, signal) });
}

/** Totales de varios meses para la gráfica de evolución, usando el resumen del panel (más liviano que el informe). */
export function useEvolucion(meses: string[]) {
  return useQueries({
    queries: meses.map((m) => {
      const { desde, hasta } = limitesDeMes(m);
      return {
        queryKey: ["evolucion", m],
        queryFn: ({ signal }: { signal: AbortSignal }) => api.get<Tablero>(`/dashboard/summary?desde=${desde}&hasta=${hasta}&dias_vencimientos=1`, signal),
      };
    }),
  });
}

/** Descarga el CSV del mes (requiere el permiso de exportación; el backend lo valida y lo audita). */
export async function descargarInformeCsv(mes: string): Promise<void> {
  const blob = await api.descargar(`/reports/monthly?mes=${mes}&formato=csv`);
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `informe-${mes}.csv`;
  enlace.click();
  URL.revokeObjectURL(url);
}