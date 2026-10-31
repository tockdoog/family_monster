// frontend/src/features/obligations/components/FormularioObligacion.tsx
// Alta de una obligación (solo administradores). El botón se bloquea al enviar.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useCategorias } from "@/features/categories/api";
import { useIntegrantes } from "@/features/members/api";
import { mensajeError } from "@/lib/errores";
import { normalizarPesos } from "@/lib/pesos";
import { useCrearObligacion } from "../api";
import { esquemaObligacion, type DatosObligacion } from "../schemas";

/** Crea la obligación y cierra solo cuando el backend confirma. */
export function FormularioObligacion({ onListo, onCancelar }: { onListo: () => void; onCancelar: () => void }) {
  const crear = useCrearObligacion();
  const categorias = useCategorias();
  const integrantes = useIntegrantes();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosObligacion>({
    resolver: zodResolver(esquemaObligacion),
    defaultValues: { descripcion: "", categoriaId: "", importe: "", fechaVencimiento: "", acreedor: "", responsableId: "" },
  });

  // Envía los datos a la API; los errores del backend se muestran tal cual.
  const enviar = handleSubmit(async (d) => {
    setErrorServidor(null);
    try {
      await crear.mutateAsync({
        descripcion: d.descripcion,
        categoria_id: d.categoriaId,
        importe_original: Number(normalizarPesos(d.importe)),
        fecha_vencimiento: d.fechaVencimiento,
        acreedor: d.acreedor,
        responsable_id: d.responsableId || undefined,
      });
      onListo();
    } catch (e) {
      setErrorServidor(mensajeError(e, "No pudimos registrar la obligación. Intenta de nuevo."));
    }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <Input etiqueta="¿Qué se debe?" placeholder="Ej. Factura de energía" error={errors.descripcion?.message} {...register("descripcion")} />
      <Input etiqueta="¿A quién se le debe?" placeholder="Ej. Empresa de energía" error={errors.acreedor?.message} {...register("acreedor")} />
      <Select etiqueta="Categoría" error={errors.categoriaId?.message} {...register("categoriaId")}>
        <option value="">Elige una categoría</option>
        {categorias.data?.filter((c) => c.activa).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
      </Select>
      <Input etiqueta="Valor (COP)" inputMode="numeric" placeholder="120.000" error={errors.importe?.message} {...register("importe")} />
      <Input etiqueta="Fecha de vencimiento" type="date" error={errors.fechaVencimiento?.message} {...register("fechaVencimiento")} />
      <Select etiqueta="Responsable (opcional)" {...register("responsableId")}>
        <option value="">Sin responsable</option>
        {integrantes.data?.filter((i) => i.activo).map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
      </Select>
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
        <Button type="submit" cargando={crear.isPending} className="flex-1">Registrar</Button>
      </div>
    </form>
  );
}