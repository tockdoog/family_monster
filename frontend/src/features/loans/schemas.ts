// frontend/src/features/loans/schemas.ts
// Validación de los formularios de préstamos y conversión al cuerpo de la API (el backend vuelve a validar todo).

import { z } from "zod";
import { hoy } from "@/features/transactions/schemas";
import { MENSAJE_IMPORTE, esImportePositivo, normalizarPesos } from "@/lib/pesos";
import type { NuevoPagoCuota, NuevoPrestamo, TipoPrestamo } from "./types";

const fechaNoFutura = (v: string) => v === "" || v <= hoy();

/** Alta de préstamo. Las cuentas y la contraparte exigidas dependen del tipo. */
export const esquemaPrestamo = z
  .object({
    tipo: z.enum(["entre_integrantes", "al_hogar", "del_hogar"]),
    importe: z.string().refine(esImportePositivo, MENSAJE_IMPORTE),
    numeroCuotas: z.string().refine((v) => /^[1-9]\d{0,2}$/.test(v) && Number(v) <= 360, "Escribe entre 1 y 360 cuotas."),
    totalAPagar: z.string().refine((v) => v === "" || esImportePositivo(v), MENSAJE_IMPORTE),
    prestamistaId: z.string(),
    prestatarioId: z.string(),
    contraparteNombre: z.string().trim().max(120, "El nombre es demasiado largo."),
    cuentaOrigenId: z.string(),
    cuentaDestinoId: z.string(),
    fecha: z.string().refine(fechaNoFutura, "La fecha no puede ser futura."),
    primerVencimiento: z.string(),
    condiciones: z.string().trim().max(1000, "El texto es demasiado largo."),
  })
  .superRefine((d, ctx) => {
    const falta = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });
    if (d.tipo === "entre_integrantes") {
      if (!d.prestamistaId) falta("prestamistaId", "Elige quién presta.");
      if (!d.prestatarioId) falta("prestatarioId", "Elige quién recibe el préstamo.");
      if (d.prestamistaId && d.prestamistaId === d.prestatarioId) falta("prestatarioId", "Quien presta y quien recibe deben ser distintos.");
      if (!d.cuentaOrigenId) falta("cuentaOrigenId", "Elige la cuenta personal de quien presta.");
      if (!d.cuentaDestinoId) falta("cuentaDestinoId", "Elige la cuenta personal de quien recibe.");
    }
    if (d.tipo === "al_hogar") {
      if (!d.prestamistaId && !d.contraparteNombre) falta("contraparteNombre", "Escribe el nombre de quien presta.");
      if (!d.cuentaDestinoId) falta("cuentaDestinoId", "Elige el fondo común que recibe el dinero.");
    }
    if (d.tipo === "del_hogar") {
      if (!d.prestatarioId && !d.contraparteNombre) falta("contraparteNombre", "Escribe el nombre de quien recibe.");
      if (!d.cuentaOrigenId) falta("cuentaOrigenId", "Elige el fondo común que presta el dinero.");
    }
  });
export type DatosPrestamo = z.infer<typeof esquemaPrestamo>;

/** Envía solo los campos que aplican al tipo de préstamo. */
export function aSolicitudPrestamo(d: DatosPrestamo): NuevoPrestamo {
  const entre = d.tipo === "entre_integrantes";
  const usaPrestamista = entre || (d.tipo === "al_hogar" && d.prestamistaId !== "");
  const usaPrestatario = entre || (d.tipo === "del_hogar" && d.prestatarioId !== "");
  const externo = d.tipo !== "entre_integrantes" && !(d.tipo === "al_hogar" ? d.prestamistaId : d.prestatarioId);
  return {
    tipo: d.tipo,
    importe: Number(normalizarPesos(d.importe)),
    numero_cuotas: Number(d.numeroCuotas),
    prestamista_integrante_id: usaPrestamista ? d.prestamistaId : undefined,
    prestatario_integrante_id: usaPrestatario ? d.prestatarioId : undefined,
    contraparte_nombre: externo ? d.contraparteNombre : undefined,
    total_a_pagar: d.totalAPagar ? Number(normalizarPesos(d.totalAPagar)) : undefined,
    fecha: d.fecha || undefined,
    primer_vencimiento: d.primerVencimiento || undefined,
    condiciones: d.condiciones || undefined,
    cuenta_origen_id: d.tipo !== "al_hogar" ? d.cuentaOrigenId : undefined,
    cuenta_destino_id: d.tipo !== "del_hogar" ? d.cuentaDestinoId : undefined,
  };
}

/** Pago de cuota: las cuentas exigidas dependen del tipo del préstamo. */
export const esquemaPagoCuota = (tipo: TipoPrestamo) =>
  z
    .object({
      cuotaNumero: z.string().min(1, "Elige la cuota."),
      importe: z.string().refine(esImportePositivo, MENSAJE_IMPORTE),
      cuentaOrigenId: z.string(),
      cuentaDestinoId: z.string(),
      fecha: z.string().refine(fechaNoFutura, "La fecha no puede ser futura."),
    })
    .superRefine((d, ctx) => {
      const falta = (path: string, message: string) => ctx.addIssue({ code: "custom", path: [path], message });
      if (tipo !== "del_hogar" && !d.cuentaOrigenId) falta("cuentaOrigenId", "Elige la cuenta con la que se paga.");
      if (tipo !== "al_hogar" && !d.cuentaDestinoId) falta("cuentaDestinoId", "Elige la cuenta que recibe el dinero.");
    });
export type DatosPagoCuota = z.infer<ReturnType<typeof esquemaPagoCuota>>;

/** Convierte el formulario en el cuerpo de la API. */
export function aSolicitudPagoCuota(tipo: TipoPrestamo, d: DatosPagoCuota): NuevoPagoCuota {
  return {
    cuota_numero: Number(d.cuotaNumero),
    importe: Number(normalizarPesos(d.importe)),
    cuenta_origen_id: tipo !== "del_hogar" ? d.cuentaOrigenId : undefined,
    cuenta_destino_id: tipo !== "al_hogar" ? d.cuentaDestinoId : undefined,
    fecha: d.fecha || undefined,
  };
}