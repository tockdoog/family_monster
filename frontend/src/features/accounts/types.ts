// frontend/src/features/accounts/types.ts
// Textos en español para los tipos de cuenta del backend.

/** Etiqueta legible de cada tipo (accounts/schemas.py → tipo). */
export const ETIQUETA_TIPO: Record<string, string> = {
  efectivo: "Efectivo",
  banco: "Cuenta bancaria",
  personal: "Fondo personal",
  otra: "Otra cuenta",
};