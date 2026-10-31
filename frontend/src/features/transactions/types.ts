// frontend/src/features/transactions/types.ts
// Tipos y textos de movimientos según transactions/schemas.py y transactions/router.py.

import type { Pesos } from "@/types/finanzas";

/** Efecto del movimiento en una cuenta: positivo entra dinero, negativo sale. */
export interface LineaMovimiento {
  cuenta_id: string;
  importe: Pesos;
}

/** Movimiento tal como lo entrega el backend (MovimientoSalida). */
export interface Movimiento {
  id: string;
  tipo: string;
  estado: string;
  fecha: string;
  descripcion: string;
  importe: Pesos;
  lineas: LineaMovimiento[];
  pagador_id: string | null;
  beneficiario_id: string | null;
  categoria_id: string | null;
  registrado_por: string;
  reversa_de_id: string | null;
  motivo: string | null;
  creado_en: string;
}

/** Cuerpo de POST /transactions. */
export interface NuevoMovimiento {
  tipo: "ingreso" | "gasto" | "transferencia";
  importe: number;
  descripcion: string;
  fecha?: string;
  cuenta_origen_id?: string;
  cuenta_destino_id?: string;
  categoria_id?: string;
  pagador_id?: string;
}

/** Nombre en español de cada tipo de movimiento. */
export const ETIQUETA_MOVIMIENTO: Record<string, string> = {
  ingreso: "Ingreso",
  gasto: "Gasto",
  transferencia: "Transferencia",
  reversion: "Reversión",
  aporte: "Aporte",
  reembolso: "Reembolso",
  pago_obligacion: "Pago de factura",
  desembolso_prestamo: "Desembolso de préstamo",
  pago_cuota: "Pago de cuota",
};

/** Filtros del listado (cadena vacía = sin filtrar). */
export interface FiltrosMovimientos {
  tipo: string;
  estado: string;
  cuentaId: string;
  desde: string;
  hasta: string;
}

export const FILTROS_VACIOS: FiltrosMovimientos = { tipo: "", estado: "", cuentaId: "", desde: "", hasta: "" };