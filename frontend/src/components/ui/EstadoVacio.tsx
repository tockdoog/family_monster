// frontend/src/components/ui/EstadoVacio.tsx
// Mensaje amable cuando todavía no hay datos que mostrar (aparece con una entrada suave).

import { motion } from "motion/react";

/** Estado vacío con título y explicación útil. */
export function EstadoVacio({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}
      className="rounded-xl border-2 border-dashed border-lavanda/60 p-6 text-center">
      <p className="font-bold text-morado">{titulo}</p>
      <p className="mt-1 text-sm text-texto-suave">{texto}</p>
    </motion.div>
  );
}