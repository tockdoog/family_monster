// frontend/src/features/auth/BienvenidaPage.tsx
// Pantalla de bienvenida (ruta "/"): identidad, monstruo y acceso al ingreso.

import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";
import { Bienvi } from "@/components/monsters/Bienvi";

/** Primera pantalla de la app. Si ya hay sesión, el botón lleva directo al panel. */
export function BienvenidaPage() {
  const { sesion } = useAuth();
  return (
    <main className="grid min-h-screen place-items-center bg-linear-to-b from-morado-profundo to-morado px-6 py-10 text-blanco">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex max-w-md flex-col items-center text-center"
      >
        <Bienvi className="h-48 w-48" />
        <h1 className="mt-4 text-4xl font-extrabold">Familia Monster</h1>
        <p className="mt-3 text-lg text-lavanda">
          Las finanzas de tu hogar, claras y en un solo lugar: dinero disponible, aportes, facturas y préstamos.
        </p>
        <Link
          to={sesion ? "/panel" : "/ingresar"}
          className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-blanco px-8 font-bold text-morado transition-colors hover:bg-lavanda"
        >
          {sesion ? "Ir a mi panel" : "Ingresar"}
        </Link>
      </motion.div>
    </main>
  );
}