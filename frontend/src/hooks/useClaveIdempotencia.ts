// frontend/src/hooks/useClaveIdempotencia.ts
// Clave de idempotencia por intento: un reintento del mismo envío no duplica la operación.

import { useRef } from "react";
import { ErrorApi, crearClaveIdempotencia } from "@/services/api/client";

/** Mantiene una clave estable y la renueva solo cuando el backend rechazó el envío (4xx). */
export function useClaveIdempotencia() {
  const clave = useRef(crearClaveIdempotencia());
  return {
    obtener: () => clave.current,
    // Un rechazo 4xx significa que no se aplicó nada: el siguiente intento necesita otra clave.
    alFallar: (error: unknown) => {
      if (error instanceof ErrorApi && error.estado >= 400 && error.estado < 500) clave.current = crearClaveIdempotencia();
    },
  };
}