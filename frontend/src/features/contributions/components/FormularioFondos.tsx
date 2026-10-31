// frontend/src/features/contributions/components/FormularioFondos.tsx
// Registro de aporte o reembolso en dos pasos: datos y confirmación.

import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasoConfirmacion } from "@/components/ui/PasoConfirmacion";
import { Select } from "@/components/ui/Select";
import { useClaveIdempotencia } from "@/hooks/useClaveIdempotencia";
import { hoy } from "@/features/transactions/schemas";
import { formatCOP } from "@/lib/formatCOP";
import { mensajeError } from "@/lib/errores";
import { normalizarPesos } from "@/lib/pesos";
import type { Cuenta } from "@/types/finanzas";
import type { Integrante } from "@/features/members/types";
import { useRegistrarFondos } from "../api";
import { aSolicitudFondos, esquemaFondos, type DatosFondos, type ModoFondos } from "../schemas";

interface Props {
  modo: ModoFondos;
  integrantes: Integrante[];
  cuentas: Cuenta[];
  inicial?: { integranteId: string; importe: string };
  onListo: () => void;
  onCancelar: () => void;
}

/** Formulario guiado; solo se envía tras confirmar el resumen. */
export function FormularioFondos({ modo, integrantes, cuentas, inicial, onListo, onCancelar }: Props) {
  const registrar = useRegistrarFondos(modo);
  const clave = useClaveIdempotencia();
  const [resumen, setResumen] = useState<DatosFondos | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const resolver = useMemo(() => zodResolver(esquemaFondos(modo)), [modo]);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<DatosFondos>({
    resolver,
    defaultValues: { integranteId: inicial?.integranteId ?? "", importe: inicial?.importe ?? "", cuentaOrigenId: "", cuentaDestinoId: "", fecha: "", descripcion: "" },
  });

  const activas = cuentas.filter((c) => c.activa);
  const comunes = activas.filter((c) => c.es_fondo_comun);
  const integranteId = watch("integranteId");
  const personales = activas.filter((c) => !c.es_fondo_comun && c.propietario_id === integranteId);
  const nombre = (id: string) => activas.find((c) => c.id === id)?.nombre ?? "—";
  const opciones = (lista: Cuenta[]) => lista.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>);

  // Envía a la API tras la confirmación; si falla, vuelve al formulario con el mensaje.
  const confirmar = async () => {
    if (!resumen) return;
    setErrorServidor(null);
    try {
      await registrar.mutateAsync({ datos: aSolicitudFondos(resumen), clave: clave.obtener() });
      onListo();
    } catch (e) {
      setErrorServidor(mensajeError(e, "No pudimos registrar la operación. Intenta de nuevo."));
      clave.alFallar(e);
      setResumen(null);
    }
  };

  return (
    <>
      <form hidden={resumen !== null} onSubmit={handleSubmit(setResumen)} noValidate className="space-y-4">
        <Select etiqueta="Integrante" error={errors.integranteId?.message} {...register("integranteId")}>
          <option value="">Elige un integrante</option>
          {integrantes.filter((i) => i.activo).map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
        </Select>
        <Input etiqueta="Importe (COP)" inputMode="numeric" placeholder="100.000" error={errors.importe?.message} {...register("importe")} />
        {modo === "aporte" ? (
          <>
            <Select etiqueta="Fondo común que recibe" error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}>
              <option value="">Elige una cuenta</option>{opciones(comunes)}
            </Select>
            <Select etiqueta="¿De dónde sale el dinero?" {...register("cuentaOrigenId")}>
              <option value="">Entra desde fuera del sistema</option>{opciones(personales)}
            </Select>
          </>
        ) : (
          <>
            <Select etiqueta="Fondo común que devuelve" error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}>
              <option value="">Elige una cuenta</option>{opciones(comunes)}
            </Select>
            <Select etiqueta="Cuenta personal que recibe" error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}>
              <option value="">Elige una cuenta</option>{opciones(personales)}
            </Select>
          </>
        )}
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
          texto="Revisa antes de registrar. Después solo se corrige con una reversión."
          cargando={registrar.isPending}
          onVolver={() => setResumen(null)}
          onConfirmar={() => void confirmar()}
          filas={[
            ["Operación", modo === "aporte" ? "Aporte" : "Reembolso"],
            ["Integrante", integrantes.find((i) => i.id === resumen.integranteId)?.nombre ?? "—"],
            ["Importe", formatCOP(normalizarPesos(resumen.importe))],
            ...(resumen.cuentaOrigenId ? [["Sale de", nombre(resumen.cuentaOrigenId)] as [string, string]] : []),
            ...(resumen.cuentaDestinoId ? [["Entra a", nombre(resumen.cuentaDestinoId)] as [string, string]] : []),
          ]}
        />
      )}
    </>
  );
}