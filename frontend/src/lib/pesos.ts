// frontend/src/lib/pesos.ts
// Utilidad compartida para interpretar importes escritos por el usuario.

/** Quita puntos, espacios y "$" para aceptar entradas como "1.500.000" o "$ 200000". */
export const normalizarPesos = (texto: string): string => texto.replace(/[\s.$]/g, "");