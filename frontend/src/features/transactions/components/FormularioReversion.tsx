// frontend/src/features/transactions/components/FormularioReversion.tsx
// Confirmación de reversión: exige un motivo y deja el rastro en el backend.

import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { formatCOP } from "@/lib/formatCOP";
import { ErrorApi, crearClaveIdempotencia } from "@/services/api/client";
import { useRevertirMovimiento } from "../api";
import { esquemaReversion, type DatosReversion } from "../schemas";
import type { Movimiento } from "../types";

/** Pide el motivo y revierte el movimiento indicado. */
export function FormularioReversion({ movimiento, onListo, onCancelar }: { movimiento: Movimiento; onListo: () => void; onCancelar: () => void }) {
  const revertir = useRevertirMovimiento();
  const clave = useRef(crearClaveIdempotencia());
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosReversion>({ resolver: zodResolver(esquemaReversion), defaultValues: { motivo: "" } });

  // Envía la reversión; si el backend la rechaza, el usuario ve el motivo.
  const enviar = handleSubmit(async ({ motivo }) => {
    setErrorServidor(null);
    try {
      await revertir.mutateAsync({ id: movimiento.id, motivo, clave: clave.current });
      onListo();
    } catch (e) {
      setErrorServidor(e instanceof ErrorApi ? e.message : "No pudimos revertir el movimiento.");
      if (e instanceof ErrorApi && e.estado >= 400 && e.estado < 500) clave.current = crearClaveIdempotencia();
    }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <p className="text-texto-suave">
        Vas a revertir «{movimiento.descripcion}» por {formatCOP(movimiento.importe)}. El dinero volverá a las cuentas y el movimiento quedará marcado como revertido.
      </p>
      <Input etiqueta="Motivo de la reversión" error={errors.motivo?.message} {...register("motivo")} />
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" onClick={onCancelar} className="flex-1">Cancelar</Button>
        <Button type="submit" variante="danger" cargando={revertir.isPending} className="flex-1">Revertir</Button>
      </div>
    </form>
  );
}