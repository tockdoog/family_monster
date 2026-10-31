// frontend/src/features/loans/components/FormularioPagoCuota.tsx
// Pago de una cuota en dos pasos: datos y confirmación. Las cuentas cambian según el tipo de préstamo.

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasoConfirmacion } from "@/components/ui/PasoConfirmacion";
import { Select } from "@/components/ui/Select";
import { hoy } from "@/features/transactions/schemas";
import { useClaveIdempotencia } from "@/hooks/useClaveIdempotencia";
import { formatCOP } from "@/lib/formatCOP";
import { mensajeError } from "@/lib/errores";
import { normalizarPesos } from "@/lib/pesos";
import type { Cuenta } from "@/types/finanzas";
import { usePagarCuota } from "../api";
import { aSolicitudPagoCuota, esquemaPagoCuota, type DatosPagoCuota } from "../schemas";
import type { Prestamo } from "../types";

/** Pago total o parcial de una cuota pendiente. */
export function FormularioPagoCuota({ prestamo, cuentas, onListo, onCancelar }: { prestamo: Prestamo; cuentas: Cuenta[]; onListo: () => void; onCancelar: () => void }) {
  const pagar = usePagarCuota();
  const clave = useClaveIdempotencia();
  const [resumen, setResumen] = useState<DatosPagoCuota | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const pendientes = prestamo.cuotas.filter((c) => Number(c.saldo) > 0);
  const resolver = useMemo(() => zodResolver(esquemaPagoCuota(prestamo.tipo)), [prestamo.tipo]);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<DatosPagoCuota>({
    resolver,
    defaultValues: { cuotaNumero: String(pendientes[0]?.numero ?? ""), importe: pendientes[0]?.saldo ?? "", cuentaOrigenId: "", cuentaDestinoId: "", fecha: "" },
  });

  // Cuentas permitidas según el tipo (ver loans/schemas.py → SolicitudPagoCuota).
  const activas = cuentas.filter((c) => c.activa);
  const comunes = activas.filter((c) => c.es_fondo_comun);
  const personalesDe = (id: string | null) => activas.filter((c) => !c.es_fondo_comun && id !== null && c.propietario_id === id);
  const entre = prestamo.tipo === "entre_integrantes";
  const origenes = entre ? personalesDe(prestamo.prestatario_integrante_id) : comunes;
  const destinos = entre ? personalesDe(prestamo.prestamista_integrante_id) : comunes;
  const opciones = (l: Cuenta[]) => l.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>);
  const nombre = (id: string) => activas.find((c) => c.id === id)?.nombre ?? "—";
  const cuotaElegida = pendientes.find((c) => String(c.numero) === watch("cuotaNumero"));

  // Envía el pago tras la confirmación; si falla vuelve al formulario con el mensaje.
  const confirmar = async () => {
    if (!resumen) return;
    setErrorServidor(null);
    try {
      await pagar.mutateAsync({ id: prestamo.id, datos: aSolicitudPagoCuota(prestamo.tipo, resumen), clave: clave.obtener() });
      onListo();
    } catch (e) {
      setErrorServidor(mensajeError(e, "No pudimos registrar el pago. Intenta de nuevo."));
      clave.alFallar(e);
      setResumen(null);
    }
  };

  return (
    <>
      <form hidden={resumen !== null} onSubmit={handleSubmit(setResumen)} noValidate className="space-y-4">
        <Select etiqueta="Cuota" error={errors.cuotaNumero?.message} {...register("cuotaNumero")}>
          {pendientes.map((c) => <option key={c.id} value={c.numero}>Cuota {c.numero} · {formatCOP(c.saldo)}</option>)}
        </Select>
        {cuotaElegida && <p className="text-sm text-texto-suave">Falta por pagar de esta cuota: {formatCOP(cuotaElegida.saldo)}</p>}
        <Input etiqueta="Importe a pagar (COP)" inputMode="numeric" error={errors.importe?.message} {...register("importe")} />
        {prestamo.tipo !== "del_hogar" && (
          <Select etiqueta={entre ? "Cuenta personal de quien paga" : "Fondo común que paga"} error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}>
            <option value="">Elige una cuenta</option>{opciones(origenes)}
          </Select>
        )}
        {prestamo.tipo !== "al_hogar" && (
          <Select etiqueta={entre ? "Cuenta personal de quien cobra" : "Fondo común que recibe"} error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}>
            <option value="">Elige una cuenta</option>{opciones(destinos)}
          </Select>
        )}
        <Input etiqueta="Fecha (opcional, por defecto hoy)" type="date" max={hoy()} error={errors.fecha?.message} {...register("fecha")} />
        {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
        <div className="flex gap-3">
          <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
          <Button type="submit" className="flex-1">Revisar</Button>
        </div>
      </form>
      {resumen && (
        <PasoConfirmacion
          texto="Revisa el pago antes de registrarlo."
          cargando={pagar.isPending}
          etiqueta="Confirmar pago"
          onVolver={() => setResumen(null)}
          onConfirmar={() => void confirmar()}
          filas={[
            ["Cuota", resumen.cuotaNumero],
            ["Importe", formatCOP(normalizarPesos(resumen.importe))],
            ...(prestamo.tipo !== "del_hogar" ? [["Sale de", nombre(resumen.cuentaOrigenId)] as [string, string]] : []),
            ...(prestamo.tipo !== "al_hogar" ? [["Entra a", nombre(resumen.cuentaDestinoId)] as [string, string]] : []),
          ]}
        />
      )}
    </>
  );
}