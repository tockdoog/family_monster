// frontend/src/components/ui/EstadoVacio.tsx
// Mensaje amable cuando todavía no hay datos que mostrar.

/** Estado vacío con título y explicación útil. */
export function EstadoVacio({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-lavanda/60 p-6 text-center">
      <p className="font-bold text-morado">{titulo}</p>
      <p className="mt-1 text-sm text-texto-suave">{texto}</p>
    </div>
  );
}