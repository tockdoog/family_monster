// frontend/src/components/monsters/Bienvi.tsx
// Bienvi: monstruo original de bienvenida (SVG liviano). Flota suave, parpadea y saluda al aparecer.
// Las animaciones están en globals.css y se desactivan con prefers-reduced-motion.

/** Monstruo morado sonriente que saluda con la mano. */
export function Bienvi({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" role="img" aria-label="Bienvi, el monstruo de bienvenida saludando" className={`bienvi-flota ${className ?? ""}`}>
      {/* Cuernitos */}
      <path d="M62 52 L72 20 L90 46 Z" fill="var(--color-lavanda)" />
      <path d="M138 52 L128 20 L110 46 Z" fill="var(--color-lavanda)" />
      {/* Cuerpo */}
      <path d="M100 38c-44 0-68 30-68 78 0 32 22 52 68 52s68-20 68-52c0-48-24-78-68-78Z" fill="var(--color-violeta)" />
      {/* Barriga clara */}
      <ellipse cx="100" cy="142" rx="34" ry="22" fill="var(--color-lavanda)" opacity="0.45" />
      {/* Brazo que saluda (se mueve desde el hombro) */}
      <path className="bienvi-saludo" d="M160 112c18-6 26-24 20-38" stroke="var(--color-violeta)" strokeWidth="14" strokeLinecap="round" fill="none" />
      {/* Ojos (parpadean cada pocos segundos) */}
      <g className="bienvi-parpadeo">
        <circle cx="76" cy="98" r="16" fill="var(--color-blanco)" />
        <circle cx="124" cy="98" r="16" fill="var(--color-blanco)" />
        <circle cx="79" cy="100" r="7" fill="var(--color-morado-profundo)" />
        <circle cx="121" cy="100" r="7" fill="var(--color-morado-profundo)" />
      </g>
      {/* Sonrisa */}
      <path d="M78 132c12 14 32 14 44 0" stroke="var(--color-morado-profundo)" strokeWidth="6" strokeLinecap="round" fill="none" />
    </svg>
  );
}