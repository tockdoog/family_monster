// frontend/src/features/members/components/FormularioIntegrante.tsx
// Alta de un integrante (solo administradores).

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { mensajeError } from "@/lib/errores";
import { useCrearIntegrante } from "../api";
import { esquemaIntegrante, type DatosIntegrante } from "../schemas";

/** Registra al integrante; el acceso a la app se otorga después, de forma separada. */
export function FormularioIntegrante({ onListo, onCancelar }: { onListo: () => void; onCancelar: () => void }) {
  const crear = useCrearIntegrante();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosIntegrante>({ resolver: zodResolver(esquemaIntegrante), defaultValues: { nombre: "" } });

  // Envía el nombre; solo se cierra si el backend confirma.
  const enviar = handleSubmit(async ({ nombre }) => {
    setErrorServidor(null);
    try { await crear.mutateAsync(nombre); onListo(); } catch (e) { setErrorServidor(mensajeError(e, "No pudimos registrar al integrante.")); }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <Input etiqueta="Nombre del integrante" placeholder="Ej. María Pérez" error={errors.nombre?.message} {...register("nombre")} />
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
        <Button type="submit" cargando={crear.isPending} className="flex-1">Registrar</Button>
      </div>
    </form>
  );
}