// frontend/src/features/dashboard/types.ts
// Tipos de la respuesta de GET /dashboard/summary (reports/schemas.py → TableroSalida).

import type { Cuenta, Pesos, ResumenIntegrante } from "@/types/finanzas";

export interface TotalesPeriodo {
  ingresos: Pesos;
  aportes: Pesos;
  gastos: Pesos;
  pagos_de_prestamos: Pesos;
  balance_operativo: Pesos;
}

export interface GastoPorCategoria {
  categoria_id: string | null;
  categoria: string;
  importe: Pesos;
}

export interface ResumenObligaciones {
  pendientes_cantidad: number;
  saldo_pendiente_total: Pesos;
  vencidas_cantidad: number;
  saldo_vencido: Pesos;
}

export interface ResumenPrestamos {
  activos_cantidad: number;
  saldo_pendiente_total: Pesos;
  cuotas_pendientes_cantidad: number;
}

export interface Vencimiento {
  tipo: "obligacion" | "cuota";
  referencia_id: string;
  descripcion: string;
  fecha_vencimiento: string;
  saldo: Pesos;
  vencido: boolean;
}

export interface Tablero {
  desde: string;
  hasta: string;
  cuentas: Cuenta[];
  saldo_total: Pesos;
  totales: TotalesPeriodo;
  gastos_por_categoria: GastoPorCategoria[];
  aportes: ResumenIntegrante[];
  gastos_sin_distribuir: Pesos;
  obligaciones: ResumenObligaciones;
  prestamos: ResumenPrestamos;
  proximos_vencimientos: Vencimiento[];
}