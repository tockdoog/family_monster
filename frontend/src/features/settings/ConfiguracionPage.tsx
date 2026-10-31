// frontend/src/features/settings/ConfiguracionPage.tsx
// Configuración (ruta "/configuracion"): perfil de la sesión y categorías del hogar.

import { useAuth } from "@/app/providers/AuthProvider";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SeccionCategorias } from "@/features/categories/components/SeccionCategorias";
import { ETIQUETA_ROL } from "@/features/members/types";

/** Solo incluye opciones con soporte real en el backend. */
export function ConfiguracionPage() {
  const { sesion } = useAuth();
  if (!sesion) return null;
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-morado">Configuración</h1>
        <p className="text-texto-suave">Tu cuenta y las categorías del hogar.</p>
      </div>

      <Card>
        <h2 className="mb-3 text-lg font-extrabold text-morado">Mi perfil</h2>
        <div className="flex items-center gap-3">
          <Avatar nombre={sesion.usuario.nombre_completo} className="size-14 text-lg" />
          <div className="min-w-0">
            <p className="font-extrabold text-texto">{sesion.usuario.nombre_completo}</p>
            <p className="truncate text-sm text-texto-suave">{sesion.usuario.email}</p>
          </div>
        </div>
        <dl className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between"><dt className="text-texto-suave">Hogar</dt><dd className="font-semibold">{sesion.hogar.nombre}</dd></div>
          <div className="flex justify-between"><dt className="text-texto-suave">Rol</dt><dd><Badge>{ETIQUETA_ROL[sesion.rol] ?? sesion.rol}</Badge></dd></div>
        </dl>
      </Card>

      <SeccionCategorias />
    </section>
  );
}