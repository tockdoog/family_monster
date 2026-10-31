// frontend/src/features/auth/LoginPage.tsx
// Inicio de sesión real (ruta "/ingresar"): valida con Zod y autentica contra /auth/login.

import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";
import { Bienvi } from "@/components/monsters/Bienvi";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ErrorApi } from "@/services/api/client";
import { esquemaLogin, type DatosLogin } from "./schemas";

/** Formulario de ingreso con mensajes claros y estado de carga. */
export function LoginPage() {
  const { sesion, entrar } = useAuth();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [verContrasena, setVerContrasena] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<DatosLogin>({ resolver: zodResolver(esquemaLogin) });

  // Con sesión activa no tiene sentido ver el login.
  if (sesion) return <Navigate to="/panel" replace />;

  // Envía las credenciales; el mensaje de error es el que entrega el backend.
  const enviar = handleSubmit(async (datos) => {
    setErrorServidor(null);
    try {
      await entrar(datos.email, datos.contrasena);
      const destino = (ubicacion.state as { desde?: string } | null)?.desde ?? "/panel";
      navegar(destino, { replace: true });
    } catch (e) {
      setErrorServidor(e instanceof ErrorApi ? e.message : "No fue posible iniciar sesión. Intenta de nuevo.");
    }
  });

  return (
    <main className="grid min-h-screen place-items-center bg-linear-to-b from-morado-profundo to-morado px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <Bienvi className="mx-auto -mb-6 h-32 w-32" />
        <Card className="pt-10">
          <h1 className="text-center text-2xl font-extrabold text-morado">Ingresa a tu hogar</h1>
          <form onSubmit={enviar} noValidate className="mt-6 space-y-4">
            <Input
              etiqueta="Correo electrónico"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <Input
              etiqueta="Contraseña"
              type={verContrasena ? "text" : "password"}
              autoComplete="current-password"
              error={errors.contrasena?.message}
              accion={
                <button
                  type="button"
                  onClick={() => setVerContrasena((v) => !v)}
                  aria-label={verContrasena ? "Ocultar contraseña" : "Mostrar contraseña"}
                  className="grid size-10 place-items-center rounded-lg text-morado-secundario"
                >
                  {verContrasena ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              }
              {...register("contrasena")}
            />
            {errorServidor && (
              <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">
                {errorServidor}
              </p>
            )}
            <Button type="submit" cargando={isSubmitting} className="w-full">
              Ingresar
            </Button>
          </form>
        </Card>
      </motion.div>
    </main>
  );
}