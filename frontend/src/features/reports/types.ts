// frontend/src/features/reports/types.ts
// Tipo del informe mensual según reports/schemas.py → InformeMensual.

import type { GastoPorCategoria, TotalesPeriodo } from "@/features/dashboard/types";
import type { Movimiento } from "@/features/transactions/types";

/** Informe de un mes: totales, gasto por categoría y movimientos (con límite de seguridad en el backend). */
export interface InformeMensual {
  mes: string;
  desde: string;
  hasta: string;
  totales: TotalesPeriodo;
  gastos_por_categoria: GastoPorCategoria[];
  total_movimientos: number;
  truncado: boolean;
  movimientos: Movimiento[];
}