// frontend/src/features/members/components/FormularioAcceso.tsx
// Otorga credenciales de la aplicación a un integrante. La contraseña nunca se guarda en el navegador.

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { mensajeError } from "@/lib/errores";
import { useOtorgarAcceso } from "../api";
import { esquemaAcceso, type DatosAcceso } from "../schemas";
import type { Integrante } from "../types";

/** Crea correo, contraseña inicial y rol para el integrante indicado. */
export function FormularioAcceso({ integrante, onListo, onCancelar }: { integrante: Integrante; onListo: () => void; onCancelar: () => void }) {
  const otorgar = useOtorgarAcceso();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors } } = useForm<DatosAcceso>({ resolver: zodResolver(esquemaAcceso), defaultValues: { email: "", contrasena: "", rol: "miembro" } });

  // Envía las credenciales; el mensaje de error es el del backend (por ejemplo, correo ya usado).
  const enviar = handleSubmit(async (datos) => {
    setErrorServidor(null);
    try { await otorgar.mutateAsync({ id: integrante.id, datos }); onListo(); } catch (e) { setErrorServidor(mensajeError(e, "No pudimos dar el acceso. Intenta de nuevo.")); }
  });

  return (
    <form onSubmit={enviar} noValidate className="space-y-4">
      <p className="text-texto-suave">Acceso para {integrante.nombre}. Comparte la contraseña inicial por un medio privado.</p>
      <Input etiqueta="Correo electrónico" type="email" autoComplete="off" error={errors.email?.message} {...register("email")} />
      <Input etiqueta="Contraseña inicial" type="password" autoComplete="new-password" error={errors.contrasena?.message} {...register("contrasena")} />
      <p className="text-sm text-texto-suave">Mínimo 12 caracteres, con al menos una letra y un número.</p>
      <Select etiqueta="Rol" {...register("rol")}>
        <option value="miembro">Miembro: solo consulta</option>
        <option value="admin">Administrador: registra y modifica todo</option>
      </Select>
      {errorServidor && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorServidor}</p>}
      <div className="flex gap-3">
        <Button type="button" variante="outline" className="flex-1" onClick={onCancelar}>Cancelar</Button>
        <Button type="submit" cargando={otorgar.isPending} className="flex-1">Dar acceso</Button>
      </div>
    </form>
  );
}