// frontend/src/lib/fechas.ts
// Formato de fechas en español. Las fechas del backend llegan como "AAAA-MM-DD" (sin hora).

// Formateador corto reutilizable: "5 nov".
const corta = new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "short" });

/** Convierte "2026-11-05" en "5 nov" sin desfase de zona horaria. */
export function formatFechaCorta(fecha: string): string {
  return corta.format(new Date(`${fecha}T00:00:00`));
}