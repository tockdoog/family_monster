// frontend/src/features/obligations/components/FormularioAnulacion.tsx
// Confirmación de anulación: exige un motivo.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { mensajeError } from "@/lib/errores";
import { useAnularObligacion } from "../api";
import { esquemaMotivo, type DatosMotivo } from "../schemas";
import type { Obligacion } from "../types";

/** Anula una obligación sin pagos; el backend rechaza la anulación si ya tiene pagos. */
export function FormularioAnulacion({ obligacion, onListo, onCancelar }: { obligacion: Obligacion; onListo: () => void; onCancelar: () => void }) {
  const anular = useAnularObligacion();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosMotivo>({ resolver: zodResolver(esquemaMotivo), defaultValues: { motivo: "" } });

  // Envía la anulación con su motivo.
  const enviar = handleSubmit(async ({ motivo }) => {
    setErrorServidor(null);
    try {
      await anular.mutateAsync({ id: obligacion.id, motivo });
      onListo();
    } catch (e) {
      setErrorServidor(mensajeError(e, "No pudimos anular la obligación."));
    }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <p className="text-texto-suave">Vas a anular «{obligacion.descripcion}». Dejará de contarse como pendiente.</p>
      <Input etiqueta="Motivo de la anulación" error={errors.motivo?.message} {...register("motivo")} />
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
        <Button type="submit" variante="danger" cargando={anular.isPending} className="flex-1">Anular</Button>
      </div>
    </form>
  );
}