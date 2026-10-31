// frontend/src/components/feedback/Avisos.tsx
// Muestra en pantalla los avisos de éxito (toasts) emitidos desde "@/lib/avisos".

import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, X } from "lucide-react";
import { quitarAviso, useAvisos } from "@/lib/avisos";

/** Contenedor de avisos: se monta una sola vez en AppProviders. */
export function Avisos() {
  // Lista reactiva de avisos activos.
  const avisos = useAvisos();

  return (
    // role="status" + aria-live: los lectores de pantalla anuncian el aviso sin interrumpir al usuario.
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 sm:inset-x-auto sm:right-4 sm:items-end"
    >
      {/* AnimatePresence permite animar la salida de cada aviso antes de quitarlo del DOM. */}
      <AnimatePresence initial={false}>
        {avisos.map((aviso) => (
          <motion.div
            key={aviso.id}
            layout
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto flex w-full max-w-sm items-center gap-3 rounded-xl border border-violet-200 bg-white px-4 py-3 text-sm text-violet-950 shadow-lg"
          >
            {/* Icono de confirmación. aria-hidden: es decorativo, el texto ya comunica el mensaje. */}
            <CheckCircle2 className="h-5 w-5 shrink-0 text-violet-600" aria-hidden="true" />
            <span className="flex-1">{aviso.texto}</span>

            {/* Botón para cerrar el aviso manualmente. */}
            <button
              type="button"
              onClick={() => quitarAviso(aviso.id)}
              aria-label="Cerrar aviso"
              className="rounded p-1 text-violet-500 transition-colors hover:bg-violet-50 hover:text-violet-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}