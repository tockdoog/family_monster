// frontend/src/components/ui/NumeroAnimado.tsx
// Monto en COP que "sube" desde cero al aparecer. El valor final siempre es el exacto del backend.

import { animate, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { formatCOP } from "@/lib/formatCOP";

/** Anima solo la presentación; los lectores de pantalla reciben el valor final directamente. */
export function NumeroAnimado({ valor, className }: { valor: string; className?: string }) {
  const reducir = useReducedMotion();
  const [texto, setTexto] = useState(() => (reducir ? formatCOP(valor) : formatCOP(0)));

  // Cuenta de 0 al valor; al terminar fija el texto exacto (sin redondeos intermedios).
  useEffect(() => {
    const destino = Number(valor);
    if (reducir || !Number.isFinite(destino)) {
      setTexto(formatCOP(valor));
      return;
    }
    const control = animate(0, destino, {
      duration: 0.9,
      ease: "easeOut",
      onUpdate: (v) => setTexto(formatCOP(Math.round(v))),
      onComplete: () => setTexto(formatCOP(valor)),
    });
    return () => control.stop();
  }, [valor, reducir]);

  return (
    <>
      <span aria-hidden className={className}>{texto}</span>
      <span className="sr-only">{formatCOP(valor)}</span>
    </>
  );
}