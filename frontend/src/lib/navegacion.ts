// frontend/src/lib/navegacion.ts
// Única fuente de los enlaces del menú. Se agrega una línea por módulo cuando su pantalla ya existe.

import { ArrowLeftRight, ChartColumn, HandCoins, Landmark, LayoutDashboard, Receipt, Settings, Users, Wallet, type LucideIcon } from "lucide-react";

/** Elemento del menú. "permiso" es opcional y solo oculta el enlace; el backend decide el acceso real. */
export interface ItemNavegacion {
  ruta: string;
  etiqueta: string;
  icono: LucideIcon;
  permiso?: string;
}

// Solo se listan pantallas construidas: así no hay enlaces a páginas inexistentes.
export const NAVEGACION: ItemNavegacion[] = [
  { ruta: "/panel", etiqueta: "Panel", icono: LayoutDashboard, permiso: "ver_finanzas" },
  { ruta: "/cuentas", etiqueta: "Cuentas", icono: Wallet, permiso: "ver_finanzas" },
  { ruta: "/movimientos", etiqueta: "Movimientos", icono: ArrowLeftRight, permiso: "ver_finanzas" },
  { ruta: "/aportes", etiqueta: "Aportes", icono: HandCoins, permiso: "ver_finanzas" },
  { ruta: "/obligaciones", etiqueta: "Obligaciones", icono: Receipt, permiso: "ver_finanzas" },
  { ruta: "/prestamos", etiqueta: "Préstamos", icono: Landmark, permiso: "ver_finanzas" },
  { ruta: "/informes", etiqueta: "Informes", icono: ChartColumn, permiso: "ver_finanzas" },
  { ruta: "/integrantes", etiqueta: "Integrantes", icono: Users, permiso: "ver_finanzas" },
  { ruta: "/configuracion", etiqueta: "Ajustes", icono: Settings, permiso: "ver_finanzas" },
];