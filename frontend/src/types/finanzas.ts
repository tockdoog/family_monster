// frontend/src/types/finanzas.ts
// Tipos compartidos según los esquemas del backend (accounts y contributions).

/** Importe en COP: el backend lo envía como texto de pesos enteros (ej. "1250000"). */
export type Pesos = string;

/** Cuenta con saldo calculado por el backend (accounts/schemas.py → CuentaSalida). */
export interface Cuenta {
  id: string;
  nombre: string;
  tipo: string;
  es_fondo_comun: boolean;
  propietario_id: string | null;
  saldo_inicial: Pesos;
  saldo_actual: Pesos;
  activa: boolean;
}

/** Estado de aportes de un integrante (contributions/schemas.py → ResumenIntegrante). */
export interface ResumenIntegrante {
  integrante_id: string;
  nombre: string;
  obligacion_esperada: Pesos;
  aportes: Pesos;
  pagos_directos: Pesos;
  reembolsos: Pesos;
  aportado_neto: Pesos;
  saldo: Pesos;
  estado: "al_dia" | "pendiente";
  reembolso_pendiente: Pesos;
}