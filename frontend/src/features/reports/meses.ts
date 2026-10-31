// frontend/src/features/reports/meses.ts
// Utilidades de meses en formato AAAA-MM (el mismo que usa el backend).

// Nombres cortos de los meses en español.
const NOMBRES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** Mes actual (hora local del dispositivo) como "AAAA-MM". */
export const mesActual = (): string => new Date().toLocaleDateString("en-CA").slice(0, 7);

/** Etiqueta corta: "2026-10" → "oct 2026". */
export function etiquetaMes(mes: string): string {
  return `${NOMBRES[Number(mes.slice(5, 7)) - 1]} ${mes.slice(0, 4)}`;
}

/** Los últimos "n" meses terminando en "hasta" (del más antiguo al más reciente). */
export function ultimosMeses(hasta: string, n: number): string[] {
  const anio = Number(hasta.slice(0, 4));
  const mes = Number(hasta.slice(5, 7));
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(anio, mes - 1 - (n - 1 - i), 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
}

/** Primer y último día del mes como "AAAA-MM-DD". */
export function limitesDeMes(mes: string): { desde: string; hasta: string } {
  const ultimo = new Date(Number(mes.slice(0, 4)), Number(mes.slice(5, 7)), 0).getDate();
  return { desde: `${mes}-01`, hasta: `${mes}-${String(ultimo).padStart(2, "0")}` };
}