// frontend/src/lib/avisos.ts
// Almacén mínimo de avisos (toasts): cualquier parte de la app puede avisar sin pasar props.

import { useSyncExternalStore } from "react";

/** Aviso visible en pantalla. */
export interface Aviso {
  id: number;
  texto: string;
}

// Duración de cada aviso en milisegundos.
const DURACION_MS = 4000;

let avisos: Aviso[] = [];
let siguienteId = 1;
const oyentes = new Set<() => void>();

// Notifica a los componentes suscritos que la lista cambió.
const emitir = () => oyentes.forEach((o) => o());

/** Quita un aviso de la lista. */
export function quitarAviso(id: number): void {
  avisos = avisos.filter((a) => a.id !== id);
  emitir();
}

/** Muestra un aviso de éxito y lo retira solo a los pocos segundos. */
export function avisar(texto: string): void {
  const id = siguienteId++;
  avisos = [...avisos, { id, texto }];
  emitir();
  setTimeout(() => quitarAviso(id), DURACION_MS);
}

// Suscripción para useSyncExternalStore.
const suscribir = (oyente: () => void) => {
  oyentes.add(oyente);
  return () => void oyentes.delete(oyente);
};

/** Lista actual de avisos (se actualiza sola). */
export function useAvisos(): Aviso[] {
  return useSyncExternalStore(suscribir, () => avisos);
}