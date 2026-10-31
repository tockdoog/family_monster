// frontend/src/features/obligations/components/FormularioPago.tsx
// Pago total o parcial de una obligación en dos pasos: datos y confirmación.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
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
import { usePagarObligacion } from "../api";
import { esquemaPago, type DatosPago } from "../schemas";
import type { Obligacion } from "../types";

interface Props {
  obligacion: Obligacion;
  cuentas: Cuenta[];
  onListo: () => void;
  onCancelar: () => void;
}

/** Sugiere pagar el saldo completo; el usuario puede abonar menos. */
export function FormularioPago({ obligacion, cuentas, onListo, onCancelar }: Props) {
  const pagar = usePagarObligacion();
  const clave = useClaveIdempotencia();
  const [resumen, setResumen] = useState<DatosPago | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const activas = cuentas.filter((c) => c.activa);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosPago>({
    resolver: zodResolver(esquemaPago),
    defaultValues: { importe: obligacion.saldo_pendiente, cuentaOrigenId: "", fecha: "", descripcion: "" },
  });

  // Envía el pago tras la confirmación; si falla vuelve al formulario con el mensaje.
  const confirmar = async () => {
    if (!resumen) return;
    setErrorServidor(null);
    try {
      await pagar.mutateAsync({
        id: obligacion.id,
        clave: clave.obtener(),
        datos: { importe: Number(normalizarPesos(resumen.importe)), cuenta_origen_id: resumen.cuentaOrigenId, fecha: resumen.fecha || undefined, descripcion: resumen.descripcion || undefined },
      });
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
        <p className="text-texto-suave">{obligacion.descripcion} · falta por pagar {formatCOP(obligacion.saldo_pendiente)}</p>
        <Input etiqueta="Importe a pagar (COP)" inputMode="numeric" error={errors.importe?.message} {...register("importe")} />
        <Select etiqueta="Cuenta con la que se paga" error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}>
          <option value="">Elige una cuenta</option>
          {activas.map((c) => <option key={c.id} value={c.id}>{c.nombre}{c.es_fondo_comun ? "" : " (personal)"}</option>)}
        </Select>
        <p className="text-sm text-texto-suave">Si pagas con un fondo personal, quedará registrado como pago hecho por esa persona a cuenta del hogar.</p>
        <Input etiqueta="Fecha (opcional, por defecto hoy)" type="date" max={hoy()} error={errors.fecha?.message} {...register("fecha")} />
        <Input etiqueta="Nota (opcional)" error={errors.descripcion?.message} {...register("descripcion")} />
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
            ["Obligación", obligacion.descripcion],
            ["Importe", formatCOP(normalizarPesos(resumen.importe))],
            ["Se paga con", activas.find((c) => c.id === resumen.cuentaOrigenId)?.nombre ?? "—"],
          ]}
        />
      )}
    </>
  );
}