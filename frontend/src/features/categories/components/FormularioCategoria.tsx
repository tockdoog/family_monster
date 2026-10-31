// frontend/src/features/categories/components/FormularioCategoria.tsx
// Crea una categoría nueva o renombra una existente.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { mensajeError } from "@/lib/errores";
import { useActualizarCategoria, useCrearCategoria, type Categoria } from "../api";
import { esquemaCategoria, type DatosCategoria } from "../schemas";

/** Con "categoria" renombra; sin ella, crea. El backend rechaza nombres repetidos. */
export function FormularioCategoria({ categoria, onListo, onCancelar }: { categoria?: Categoria; onListo: () => void; onCancelar: () => void }) {
  const crear = useCrearCategoria();
  const actualizar = useActualizarCategoria();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosCategoria>({ resolver: zodResolver(esquemaCategoria), defaultValues: { nombre: categoria?.nombre ?? "" } });
  const cargando = crear.isPending || actualizar.isPending;

  // Envía el nombre; solo se cierra si el backend confirma.
  const enviar = handleSubmit(async ({ nombre }) => {
    setErrorServidor(null);
    try {
      if (categoria) await actualizar.mutateAsync({ id: categoria.id, cambios: { nombre } });
      else await crear.mutateAsync(nombre);
      onListo();
    } catch (e) { setErrorServidor(mensajeError(e, "No pudimos guardar la categoría.")); }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <Input etiqueta="Nombre de la categoría" placeholder="Ej. Mascotas" error={errors.nombre?.message} {...register("nombre")} />
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
        <Button type="submit" cargando={cargando} className="flex-1">Guardar</Button>
      </div>
    </form>
  );
}