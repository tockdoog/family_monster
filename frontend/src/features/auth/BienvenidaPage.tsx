// frontend/src/features/auth/BienvenidaPage.tsx
// Pantalla de bienvenida (ruta "/"): los elementos entran uno tras otro y el botón reacciona al cursor.

import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";
import { Bienvi } from "@/components/monsters/Bienvi";

// Cada hijo aparece 0,12 s después del anterior.
const contenedor = { oculto: {}, visible: { transition: { staggerChildren: 0.12 } } };
const elemento = { oculto: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

/** Primera pantalla de la app. Si ya hay sesión, el botón lleva directo al panel. */
export function BienvenidaPage() {
  const { sesion } = useAuth();
  return (
    <main className="grid min-h-screen place-items-center bg-linear-to-b from-morado-profundo to-morado px-6 py-10 text-blanco">
      <motion.div variants={contenedor} initial="oculto" animate="visible" className="flex max-w-md flex-col items-center text-center">
        <motion.div variants={elemento}><Bienvi className="h-48 w-48" /></motion.div>
        <motion.h1 variants={elemento} className="mt-4 text-4xl font-extrabold">Familia Monster</motion.h1>
        <motion.p variants={elemento} className="mt-3 text-lg text-lavanda">
          Las finanzas de tu hogar, claras y en un solo lugar: dinero disponible, aportes, facturas y préstamos.
        </motion.p>
        <motion.div variants={elemento}>
          <Link
            to={sesion ? "/panel" : "/ingresar"}
            className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-blanco px-8 font-bold text-morado transition duration-150 hover:scale-105 hover:bg-lavanda active:scale-95"
          >
            {sesion ? "Ir a mi panel" : "Ingresar"}
          </Link>
        </motion.div>
      </motion.div>
    </main>
  );
}