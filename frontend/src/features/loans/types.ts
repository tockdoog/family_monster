// frontend/src/features/loans/types.ts
// Tipos y textos de préstamos según loans/schemas.py.

import type { Pesos } from "@/types/finanzas";

export type TipoPrestamo = "entre_integrantes" | "al_hogar" | "del_hogar";
export type EstadoPrestamo = "activo" | "pagado" | "anulado";
export type EstadoCuota = "pendiente" | "parcialmente_pagada" | "pagada" | "vencida";

/** Cuota con lo pagado y su estado, derivados por el backend. */
export interface Cuota {
  id: string;
  numero: number;
  fecha_vencimiento: string;
  importe: Pesos;
  pagado: Pesos;
  saldo: Pesos;
  estado: EstadoCuota;
}

/** Préstamo con saldo, estado y cuotas. */
export interface Prestamo {
  id: string;
  tipo: TipoPrestamo;
  prestamista_integrante_id: string | null;
  prestatario_integrante_id: string | null;
  contraparte_nombre: string | null;
  fecha: string;
  importe: Pesos;
  total_a_pagar: Pesos;
  pagado: Pesos;
  saldo_pendiente: Pesos;
  estado: EstadoPrestamo;
  condiciones: string | null;
  desembolso_movimiento_id: string;
  cuotas: Cuota[];
}

/** Pago de una cuota dentro del historial. */
export interface PagoCuota {
  movimiento_id: string;
  cuota_numero: number;
  fecha: string;
  importe: Pesos;
  estado_movimiento: string;
}

/** Préstamo con historial de pagos (GET /loans/{id}). */
export interface PrestamoDetalle extends Prestamo {
  pagos: PagoCuota[];
}

/** Cuerpo de POST /loans. */
export interface NuevoPrestamo {
  tipo: TipoPrestamo;
  importe: number;
  numero_cuotas: number;
  prestamista_integrante_id?: string;
  prestatario_integrante_id?: string;
  contraparte_nombre?: string;
  total_a_pagar?: number;
  fecha?: string;
  primer_vencimiento?: string;
  condiciones?: string;
  cuenta_origen_id?: string;
  cuenta_destino_id?: string;
}

/** Cuerpo de POST /loans/{id}/payments. */
export interface NuevoPagoCuota {
  cuota_numero: number;
  importe: number;
  cuenta_origen_id?: string;
  cuenta_destino_id?: string;
  fecha?: string;
}

export const ETIQUETA_TIPO_PRESTAMO: Record<TipoPrestamo, string> = {
  entre_integrantes: "Entre integrantes",
  al_hogar: "Préstamo al hogar",
  del_hogar: "Préstamo del hogar",
};

export const ETIQUETA_ESTADO_PRESTAMO: Record<EstadoPrestamo, string> = { activo: "Activo", pagado: "Pagado", anulado: "Anulado" };

export const ETIQUETA_ESTADO_CUOTA: Record<EstadoCuota, string> = {
  pendiente: "Pendiente",
  parcialmente_pagada: "Pago parcial",
  pagada: "Pagada",
  vencida: "Vencida",
};

export const TONO_CUOTA: Record<EstadoCuota, "neutro" | "exito" | "alerta" | "aviso"> = {
  pendiente: "neutro",
  parcialmente_pagada: "aviso",
  pagada: "exito",
  vencida: "alerta",
};