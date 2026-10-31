// frontend/src/lib/formatCOP.ts
// Formato único de pesos colombianos. Solo presenta el valor: el saldo oficial lo calcula el backend.

// Formateador reutilizable: separadores de miles de es-CO y sin decimales (COP entero).
const formateador = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

/** Convierte un importe (número o texto del backend) a "$ 1.234.567". Valores inválidos muestran "—". */
export function formatCOP(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  const numero = typeof valor === "string" ? Number(valor) : valor;
  return Number.isFinite(numero) ? formateador.format(numero) : "—";
}