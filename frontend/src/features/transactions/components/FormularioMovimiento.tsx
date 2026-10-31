// frontend/src/features/transactions/components/FormularioMovimiento.tsx
// Registro de ingreso, gasto o transferencia en dos pasos: datos y confirmación.

import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useCuentas } from "@/features/accounts/api";
import { useCategorias } from "@/features/categories/api";
import { useIntegrantes } from "@/features/members/api";
import { formatCOP } from "@/lib/formatCOP";
import { normalizarPesos } from "@/lib/pesos";
import { ErrorApi, crearClaveIdempotencia } from "@/services/api/client";
import { useRegistrarMovimiento } from "../api";
import { aSolicitud, esquemaMovimiento, hoy, type DatosMovimiento } from "../schemas";
import { ETIQUETA_MOVIMIENTO } from "../types";

/** Formulario guiado: el movimiento solo se envía tras la confirmación explícita. */
export function FormularioMovimiento({ onListo, onCancelar }: { onListo: () => void; onCancelar: () => void }) {
  const registrar = useRegistrarMovimiento();
  const cuentas = useCuentas();
  const categorias = useCategorias();
  const integrantes = useIntegrantes();
  // Una clave por intento: reintentar el mismo envío no duplica el movimiento.
  const clave = useRef(crearClaveIdempotencia());
  const [resumen, setResumen] = useState<DatosMovimiento | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, watch, formState: { errors } } = useForm<DatosMovimiento>({
    resolver: zodResolver(esquemaMovimiento),
    defaultValues: { tipo: "gasto", importe: "", descripcion: "", fecha: "", cuentaOrigenId: "", cuentaDestinoId: "", categoriaId: "", pagadorId: "" },
  });
  const tipo = watch("tipo");

  const cuentasActivas = (cuentas.data ?? []).filter((c) => c.activa);
  const nombreCuenta = (id: string) => cuentasActivas.find((c) => c.id === id)?.nombre ?? "—";
  const opcionesCuenta = cuentasActivas.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>);

  // Confirmado el resumen, se envía a la API y solo entonces se cierra.
  const confirmar = async () => {
    if (!resumen) return;
    setErrorServidor(null);
    try {
      await registrar.mutateAsync({ datos: aSolicitud(resumen), clave: clave.current });
      onListo();
    } catch (e) {
      setErrorServidor(e instanceof ErrorApi ? e.message : "No pudimos registrar el movimiento. Intenta de nuevo.");
      // Si el backend lo rechazó (4xx) no se aplicó nada: el nuevo intento usa otra clave.
      if (e instanceof ErrorApi && e.estado >= 400 && e.estado < 500) clave.current = crearClaveIdempotencia();
      setResumen(null);
    }
  };

  return (
    <>
      {/* Paso 1: datos */}
      <form hidden={resumen !== null} onSubmit={handleSubmit(setResumen)} noValidate className="space-y-4">
        <Select etiqueta="¿Qué quieres registrar?" {...register("tipo")}>
          <option value="gasto">Gasto</option>
          <option value="ingreso">Ingreso</option>
          <option value="transferencia">Transferencia entre cuentas</option>
        </Select>
        <Input etiqueta="Importe (COP)" inputMode="numeric" placeholder="50.000" error={errors.importe?.message} {...register("importe")} />
        <Input etiqueta="Descripción" placeholder="Ej. Mercado de la semana" error={errors.descripcion?.message} {...register("descripcion")} />
        {tipo !== "ingreso" && (
          <Select etiqueta="Cuenta de origen" error={errors.cuentaOrigenId?.message} {...register("cuentaOrigenId")}>
            <option value="">Elige una cuenta</option>{opcionesCuenta}
          </Select>
        )}
        {tipo !== "gasto" && (
          <Select etiqueta="Cuenta de destino" error={errors.cuentaDestinoId?.message} {...register("cuentaDestinoId")}>
            <option value="">Elige una cuenta</option>{opcionesCuenta}
          </Select>
        )}
        {tipo !== "transferencia" && (
          <Select etiqueta="Categoría (opcional)" {...register("categoriaId")}>
            <option value="">Sin categoría</option>
            {categorias.data?.filter((c) => c.activa).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </Select>
        )}
        {tipo === "gasto" && (
          <Select etiqueta="¿Quién pagó con su propio dinero? (opcional)" {...register("pagadorId")}>
            <option value="">Nadie, salió de la cuenta</option>
            {integrantes.data?.filter((i) => i.activo).map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
          </Select>
        )}
        <Input etiqueta="Fecha (opcional, por defecto hoy)" type="date" max={hoy()} error={errors.fecha?.message} {...register("fecha")} />
        {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
        <div className="flex gap-3">
          <Button type="button" variante="outline" onClick={onCancelar} className="flex-1">Cancelar</Button>
          <Button type="submit" className="flex-1">Revisar</Button>
        </div>
      </form>

      {/* Paso 2: confirmación */}
      {resumen && (
        <div className="space-y-4">
          <p className="text-texto-suave">Revisa antes de registrar. Después solo se puede corregir con una reversión.</p>
          <dl className="space-y-1 rounded-xl bg-fondo p-4">
            <div><dt className="inline font-semibold">Tipo: </dt><dd className="inline">{ETIQUETA_MOVIMIENTO[resumen.tipo]}</dd></div>
            <div><dt className="inline font-semibold">Importe: </dt><dd className="cifras inline">{formatCOP(normalizarPesos(resumen.importe))}</dd></div>
            <div><dt className="inline font-semibold">Descripción: </dt><dd className="inline">{resumen.descripcion}</dd></div>
            {resumen.tipo !== "ingreso" && <div><dt className="inline font-semibold">Sale de: </dt><dd className="inline">{nombreCuenta(resumen.cuentaOrigenId)}</dd></div>}
            {resumen.tipo !== "gasto" && <div><dt className="inline font-semibold">Entra a: </dt><dd className="inline">{nombreCuenta(resumen.cuentaDestinoId)}</dd></div>}
          </dl>
          <div className="flex gap-3">
            <Button type="button" variante="outline" onClick={() => setResumen(null)} className="flex-1" disabled={registrar.isPending}>Volver</Button>
            <Button type="button" onClick={() => void confirmar()} cargando={registrar.isPending} className="flex-1">Confirmar y registrar</Button>
          </div>
        </div>
      )}
    </>
  );
}