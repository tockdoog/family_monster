// frontend/src/lib/pesos.ts
// Utilidades compartidas para interpretar importes escritos por el usuario.

/** Quita puntos, espacios y "$" para aceptar entradas como "1.500.000" o "$ 200000". */
export const normalizarPesos = (texto: string): string => texto.replace(/[\s.$]/g, "");

/** True si el texto es un importe en pesos enteros mayor que cero (máx. 12 dígitos). */
export const esImportePositivo = (texto: string): boolean => /^[1-9]\d{0,11}$/.test(normalizarPesos(texto));

/** Mensaje estándar para importes inválidos. */
export const MENSAJE_IMPORTE = "Escribe un importe en pesos enteros mayor que cero.";