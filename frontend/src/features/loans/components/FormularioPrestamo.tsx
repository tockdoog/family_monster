// frontend/src/features/loans/components/FormularioPrestamo.tsx
// Alta de un préstamo (solo administradores) en dos pasos: datos y confirmación.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PasoConfirmacion } from "@/components/ui/PasoConfirmacion";
import { Select } from "@/components/ui/Select";
import { hoy } from "@/features/transactions/schemas";
import { useClaveIdempotencia } from "@/hooks/useClaveIdempotencia";
import type { Integrante } from "@/features/members/types";
import { formatCOP } from "@/lib/formatCOP";
import { mensajeError } from "@/lib/errores";
import { normalizarPesos } from "@/lib/pesos";
import type { Cuenta } from "@/types/finanzas";
import { useCrearPrestamo } from "../api";
import { aSolicitudPrestamo, esquemaPrestamo, type DatosPrestamo } from "../schemas";
import { ETIQUETA_TIPO_PRESTAMO } from "../types";

/** Al crear el préstamo se registra también el desembolso del dinero. */
export function FormularioPrestamo({ integrantes, cuentas, onListo, onCancelar }: { integrantes: Integrante[]; cuentas: Cuenta[]; onListo: () => void; onCancelar: () => void }) {
  const crear = useCrearPrestamo();
  const clave = useClaveIdempotencia();
  const [resumen, setResumen] = useState<DatosPrestamo | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<DatosPrestamo>({
    resolver: zodResolver(esquemaPrestamo),
    defaultValues: { tipo: "entre_integrantes", importe: "", numeroCuotas: "1", totalAPagar: "", prestamistaId: "", prestatarioId: "", contraparteNombre: "", cuentaOrigenId: "", cuentaDestinoId: "", fecha: "", primerVencimiento: "", condiciones: "" },
  });
  const tipo = watch("tipo");
  const prestamistaId = watch("prestamistaId");
  const prestatarioId = watch("prestatarioId");

  const activos = integrantes.filter((i) => i.activo);
  const activas = cuentas.filter((c) => c.activa);
  const comunes = activas.filter((c) => c.es_fondo_comun);
  const personalesDe = (id: string) => activas.filter((c) => !c.es_fondo_comun && c.propietario_id === id);
  const opcionesInt = activos.map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>);
  const opcionesCuenta = (l: Cuenta[]) => l.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>);

  // Un tercero aparece cuando el hogar es una de las partes y no se elige integrante.
  const pideTercero = (tipo === "al_hogar" && prestamistaId === "") || (tipo === "del_hogar" && prestatarioId === "");

  // Envía a la API tras confirmar; si falla vuelve al formulario con el mensaje.
  const confirmar = async () => {
    if (!resumen) return;
    setErrorServidor(null);
    try {
      await crear.mutateAsync({ datos: aSolicitudPrestamo(resumen), clave: clave.obtener() });
      onListo();
    } catch (e) {
      setErrorServidor(mensajeError(e, "No pudimos crear el préstamo. Intenta de nuevo."));
      clave.alFallar(e);
      setResumen(null);
    }
  };

  return (
    <>
      <form hidden={resumen !== null} onSubmit={handleSubmit(setResumen)} noValidate className="space-y-4">
        <Select etiqueta="Tipo de préstamo" {...register("tipo")}>
          {Object.entries(ETIQUETA_TIPO_PRESTAMO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
        {tipo === "entre_integrantes" && (
          <>
            <Select etiqueta="¿Quién presta?" error={errors.prestamistaId?.message} {...register("prestamistaId")}><option value="">Elige un integrante</option>{opcionesInt}</Select>
            <Select etiqueta="¿Quién recibe?" error={errors.prestatarioId?.message} {...register("prestatarioId")}><option value="">Elige un integrante</option>{opcionesInt}</Select>
            <Select etiqueta="Cuenta personal de quien presta" error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}><option value="">Elige una cuenta</option>{opcionesCuenta(personalesDe(prestamistaId))}</Select>
            <Select etiqueta="Cuenta personal de quien recibe" error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}><option value="">Elige una cuenta</option>{opcionesCuenta(personalesDe(prestatarioId))}</Select>
          </>
        )}
        {tipo === "al_hogar" && (
          <>
            <Select etiqueta="¿Quién presta al hogar?" {...register("prestamistaId")}><option value="">Un tercero (banco, persona externa)</option>{opcionesInt}</Select>
            <Select etiqueta="Fondo común que recibe el dinero" error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}><option value="">Elige una cuenta</option>{opcionesCuenta(comunes)}</Select>
          </>
        )}
        {tipo === "del_hogar" && (
          <>
            <Select etiqueta="¿A quién presta el hogar?" {...register("prestatarioId")}><option value="">Un tercero (persona externa)</option>{opcionesInt}</Select>
            <Select etiqueta="Fondo común que presta el dinero" error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}><option value="">Elige una cuenta</option>{opcionesCuenta(comunes)}</Select>
          </>
        )}
        {pideTercero && <Input etiqueta="Nombre del tercero" error={errors.contraparteNombre?.message} {...register("contraparteNombre")} />}
        <Input etiqueta="Valor prestado (COP)" inputMode="numeric" error={errors.importe?.message} {...register("importe")} />
        <Input etiqueta="Total a devolver con intereses (opcional)" inputMode="numeric" error={errors.totalAPagar?.message} {...register("totalAPagar")} />
        <Input etiqueta="Número de cuotas" inputMode="numeric" error={errors.numeroCuotas?.message} {...register("numeroCuotas")} />
        <Input etiqueta="Fecha del préstamo (opcional)" type="date" max={hoy()} error={errors.fecha?.message} {...register("fecha")} />
        <Input etiqueta="Primer vencimiento (opcional)" type="date" {...register("primerVencimiento")} />
        <Input etiqueta="Condiciones (opcional)" error={errors.condiciones?.message} {...register("condiciones")} />
        {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
        <div className="flex gap-3">
          <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
          <Button type="submit" className="flex-1">Revisar</Button>
        </div>
      </form>
      {resumen && (
        <PasoConfirmacion
          texto="Al crear el préstamo se registra el desembolso del dinero. Revisa antes de confirmar."
          cargando={crear.isPending}
          onVolver={() => setResumen(null)}
          onConfirmar={() => void confirmar()}
          filas={[
            ["Tipo", ETIQUETA_TIPO_PRESTAMO[resumen.tipo]],
            ["Valor prestado", formatCOP(normalizarPesos(resumen.importe))],
            ["Cuotas", resumen.numeroCuotas],
            ...(resumen.totalAPagar ? [["Total a devolver", formatCOP(normalizarPesos(resumen.totalAPagar))] as [string, string]] : []),
          ]}
        />
      )}
    </>
  );
}