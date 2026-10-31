// frontend/src/features/obligations/types.ts
// Tipos y textos de obligaciones según obligations/schemas.py.

import type { Pesos } from "@/types/finanzas";

export type EstadoObligacion = "pendiente" | "parcialmente_pagada" | "pagada" | "vencida" | "anulada";

/** Obligación con saldo y estado calculados por el backend. */
export interface Obligacion {
  id: string;
  descripcion: string;
  categoria_id: string;
  importe_original: Pesos;
  pagado: Pesos;
  saldo_pendiente: Pesos;
  estado: EstadoObligacion;
  fecha_creacion: string;
  fecha_vencimiento: string;
  acreedor: string;
  responsable_id: string | null;
  motivo_anulacion: string | null;
}

/** Cuerpo de POST /obligations. */
export interface NuevaObligacion {
  descripcion: string;
  categoria_id: string;
  importe_original: number;
  fecha_vencimiento: string;
  acreedor: string;
  responsable_id?: string;
}

/** Cuerpo de POST /obligations/{id}/payments. */
export interface NuevoPago {
  importe: number;
  cuenta_origen_id: string;
  fecha?: string;
  descripcion?: string;
}

export const ETIQUETA_ESTADO: Record<EstadoObligacion, string> = {
  pendiente: "Pendiente",
  parcialmente_pagada: "Pago parcial",
  pagada: "Pagada",
  vencida: "Vencida",
  anulada: "Anulada",
};

export const TONO_ESTADO: Record<EstadoObligacion, "neutro" | "exito" | "alerta" | "aviso"> = {
  pendiente: "neutro",
  parcialmente_pagada: "aviso",
  pagada: "exito",
  vencida: "alerta",
  anulada: "neutro",
};