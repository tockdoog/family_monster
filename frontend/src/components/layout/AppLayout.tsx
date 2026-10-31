// frontend/src/components/layout/AppLayout.tsx
// Estructura de la app autenticada: barra lateral (tablet/escritorio), barra inferior (móvil) y encabezado.

import { LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { NAVEGACION } from "@/lib/navegacion";

// Fecha larga en español de Colombia, calculada una sola vez.
const FECHA_HOY = new Intl.DateTimeFormat("es-CO", { dateStyle: "full" }).format(new Date());

/** Layout privado: contiene la navegación y el espacio donde se muestran las pantallas. */
export function AppLayout() {
  const { sesion, salir, puede } = useAuth();
  // Se ocultan los enlaces para los que el rol no tiene permiso (solo cosmético).
  const items = NAVEGACION.filter((i) => !i.permiso || puede(i.permiso));

  // Estilo de un enlace según esté activo o no.
  const claseEnlace = ({ isActive }: { isActive: boolean }) =>
    cn(
      "flex min-h-11 items-center gap-3 rounded-xl px-3 font-semibold transition-colors",
      isActive ? "bg-violeta text-blanco" : "text-lavanda hover:bg-morado-secundario",
    );

  return (
    <div className="min-h-screen md:pl-20 lg:pl-64">
      {/* Barra lateral: solo íconos en tablet, con texto en escritorio */}
      <aside className="fixed inset-y-0 left-0 hidden w-20 flex-col bg-morado-profundo p-3 md:flex lg:w-64">
        <p className="mb-6 px-3 pt-3 text-xl font-extrabold text-blanco">
          <span className="lg:hidden">FM</span>
          <span className="hidden lg:inline">Familia Monster</span>
        </p>
        <nav aria-label="Principal" className="space-y-1">
          {items.map(({ ruta, etiqueta, icono: Icono }) => (
            <NavLink key={ruta} to={ruta} className={claseEnlace} aria-label={etiqueta}>
              <Icono size={22} aria-hidden />
              <span className="hidden lg:inline">{etiqueta}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Encabezado: hogar, fecha y cierre de sesión */}
      <header className="flex items-center justify-between gap-3 bg-blanco px-4 py-3 shadow-tarjeta md:px-8">
        <div>
          <p className="font-extrabold text-morado">{sesion?.hogar.nombre}</p>
          <p className="text-sm capitalize text-texto-suave">{FECHA_HOY}</p>
        </div>
        <Button variante="ghost" onClick={() => void salir()} aria-label="Cerrar sesión">
          <LogOut size={20} aria-hidden />
          <span className="hidden sm:inline">Salir</span>
        </Button>
      </header>

      {/* Contenido: deja espacio inferior para la barra móvil */}
      <main className="p-4 pb-28 md:p-8 md:pb-8">
        <Outlet />
      </main>

      {/* Navegación móvil inferior, respetando el área segura del iPhone */}
      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 flex justify-around bg-morado-profundo px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden"
      >
        {items.map(({ ruta, etiqueta, icono: Icono }) => (
          <NavLink key={ruta} to={ruta} className={cn(claseEnlace({ isActive: false }), "flex-col gap-0 text-xs")}>
            {({ isActive }) => (
              <span className={cn("flex flex-col items-center", isActive ? "text-blanco" : "text-lavanda")}>
                <Icono size={22} aria-hidden />
                {etiqueta}
              </span>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}