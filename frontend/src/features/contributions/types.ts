// frontend/src/features/contributions/types.ts
// Tipos según contributions/schemas.py (ResumenAportes, ReglaSalida).

import type { Pesos, ResumenIntegrante } from "@/types/finanzas";

/** Resumen de aportes esperados y reales del período. */
export interface ResumenAportes {
  desde: string;
  hasta: string;
  integrantes: ResumenIntegrante[];
  total_esperado: Pesos;
  total_aportado_neto: Pesos;
  gastos_sin_distribuir: Pesos;
}

/** Parte de un integrante en una regla (porcentaje, parte igual o valor fijo). */
export interface ItemRegla {
  integrante_id: string;
  tipo: string;
  valor: string;
}

/** Regla de reparto con vigencia. */
export interface Regla {
  id: string;
  nombre: string;
  categoria_id: string | null;
  vigente_desde: string;
  vigente_hasta: string | null;
  items: ItemRegla[];
}

/** Cuerpo de POST /contributions y /contributions/reimbursements. */
export interface SolicitudFondos {
  integrante_id: string;
  importe: number;
  cuenta_origen_id?: string;
  cuenta_destino_id?: string;
  fecha?: string;
  descripcion?: string;
}