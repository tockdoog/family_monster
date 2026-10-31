// frontend/src/features/accounts/components/FormularioCuenta.tsx
// Formulario de nueva cuenta. El botón se bloquea al enviar para evitar duplicados.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useIntegrantes } from "@/features/members/api";
import { ErrorApi } from "@/services/api/client";
import { useCrearCuenta } from "../api";
import { esquemaCuenta, normalizarPesos, type DatosCuenta } from "../schemas";

/** Crea la cuenta y avisa al padre cuando el backend confirma. */
export function FormularioCuenta({ onListo, onCancelar }: { onListo: () => void; onCancelar: () => void }) {
  const crear = useCrearCuenta();
  const integrantes = useIntegrantes();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<DatosCuenta>({
    resolver: zodResolver(esquemaCuenta),
    defaultValues: { nombre: "", tipo: "efectivo", saldoInicial: "", propietarioId: "" },
  });
  const esPersonal = watch("tipo") === "personal";

  // Envía los datos; solo se cierra el modal si el backend confirmó la creación.
  const enviar = handleSubmit(async (d) => {
    setErrorServidor(null);
    try {
      await crear.mutateAsync({
        nombre: d.nombre,
        tipo: d.tipo,
        saldo_inicial: Number(normalizarPesos(d.saldoInicial) || "0"),
        propietario_id: d.tipo === "personal" ? d.propietarioId : undefined,
      });
      onListo();
    } catch (e) {
      setErrorServidor(e instanceof ErrorApi ? e.message : "No pudimos crear la cuenta. Intenta de nuevo.");
    }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <Input etiqueta="Nombre de la cuenta" placeholder="Ej. Efectivo de la casa" error={errors.nombre?.message} {...register("nombre")} />
      <Select etiqueta="Tipo de cuenta" error={errors.tipo?.message} {...register("tipo")}>
        <option value="efectivo">Efectivo</option>
        <option value="banco">Cuenta bancaria</option>
        <option value="personal">Fondo personal</option>
        <option value="otra">Otra cuenta</option>
      </Select>
      {/* El propietario solo aplica a fondos personales */}
      {esPersonal && (
        <Select etiqueta="Dueño del fondo" error={errors.propietarioId?.message} {...register("propietarioId")}>
          <option value="">{integrantes.isPending ? "Cargando…" : "Elige un integrante"}</option>
          {integrantes.data?.filter((i) => i.activo).map((i) => (
            <option key={i.id} value={i.id}>{i.nombre}</option>
          ))}
        </Select>
      )}
      <Input etiqueta="Saldo inicial (COP)" inputMode="numeric" placeholder="0" error={errors.saldoInicial?.message} {...register("saldoInicial")} />
      <p className="text-sm text-texto-suave">El saldo inicial no se puede editar después. Revisa que sea correcto.</p>
      {errorServidor && (
        <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">
          {errorServidor}
        </p>
      )}
      <div className="flex gap-3">
        <Button type="button" variante="outline" onClick={onCancelar} className="flex-1">
          Cancelar
        </Button>
        <Button type="submit" cargando={crear.isPending} className="flex-1">
          Crear cuenta
        </Button>
      </div>
    </form>
  );
}