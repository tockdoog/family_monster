// frontend/src/components/ui/Modal.tsx
// Ventana modal sobre <dialog> nativo: bloquea el fondo, atrapa el foco y se cierra con Esc.

import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";

interface Props {
  abierto: boolean;
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
}

/** Modal accesible. El contenido se monta solo al abrir, así los formularios empiezan limpios. */
export function Modal({ abierto, titulo, onCerrar, children }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const idTitulo = useId();

  // Sincroniza el estado "abierto" con el elemento <dialog>.
  useEffect(() => {
    const dialogo = ref.current;
    if (!dialogo) return;
    if (abierto && !dialogo.open) dialogo.showModal();
    if (!abierto && dialogo.open) dialogo.close();
  }, [abierto]);

  return (
    <dialog
      ref={ref}
      onClose={onCerrar}
      aria-labelledby={idTitulo}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-tarjeta bg-blanco p-6 shadow-tarjeta backdrop:bg-morado-profundo/60"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <h2 id={idTitulo} className="text-xl font-extrabold text-morado">
          {titulo}
        </h2>
        <button type="button" onClick={onCerrar} aria-label="Cerrar" className="grid size-10 place-items-center rounded-lg text-morado-secundario">
          <X size={20} aria-hidden />
        </button>
      </div>
      {abierto && children}
    </dialog>
  );
}