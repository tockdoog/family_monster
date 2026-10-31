// frontend/src/features/dashboard/DashboardPage.tsx
// Panel principal (ruta "/panel"): indicadores, gráficos y paneles con datos reales de /dashboard/summary.

import { Banknote, FileWarning, HandCoins, PiggyBank, TrendingDown, TrendingUp } from "lucide-react";
import { Suspense, lazy, type ReactNode } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { ErrorApi } from "@/services/api/client";
import { useTablero } from "./api";
import { IndicadorCard } from "./components/IndicadorCard";
import { PanelAportes } from "./components/PanelAportes";
import { PanelCuentas } from "./components/PanelCuentas";
import { PanelVencimientos } from "./components/PanelVencimientos";

// Los gráficos (Recharts) se descargan solo cuando el panel los necesita.
const GraficoIngresosGastos = lazy(() => import("./components/Graficos").then((m) => ({ default: m.GraficoIngresosGastos })));
const GraficoCategorias = lazy(() => import("./components/Graficos").then((m) => ({ default: m.GraficoCategorias })));

/** Sección con título dentro de una tarjeta. */
function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Card>
      <h2 className="mb-3 text-lg font-extrabold text-morado">{titulo}</h2>
      {children}
    </Card>
  );
}

/** Panel del hogar con estados de carga y de error. */
export function DashboardPage() {
  const { sesion } = useAuth();
  const { data, isPending, isError, error, refetch, isFetching } = useTablero();
  const primerNombre = sesion?.usuario.nombre_completo.split(" ")[0];

  // Carga: esqueletos con la forma del contenido final.
  if (isPending) {
    return (
      <div aria-busy className="space-y-4">
        <Skeleton className="h-8 w-56" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-72" />
      </div>
    );
  }

  // Error: mensaje claro y opción de reintentar.
  if (isError) {
    return (
      <Card role="alert">
        <p className="font-bold text-morado">No pudimos cargar tu panel</p>
        <p className="mt-1 text-texto-suave">{error instanceof ErrorApi ? error.message : "Intenta de nuevo."}</p>
        <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
      </Card>
    );
  }

  const { totales, obligaciones, prestamos } = data;
  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-morado">Hola, {primerNombre}</h1>
        <p className="text-texto-suave">Resumen del {formatFechaCorta(data.desde)} al {formatFechaCorta(data.hasta)}</p>
      </div>

      {/* Indicadores principales */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <IndicadorCard etiqueta="Dinero disponible" icono={Banknote} valor={data.saldo_total} retraso={0}
          ayuda="Suma de los saldos de todas las cuentas del hogar, según el sistema." />
        <IndicadorCard etiqueta="Ingresos" icono={TrendingUp} valor={totales.ingresos} retraso={0.05}
          ayuda="Dinero que entró en el período por sueldos, ventas u otros. No incluye aportes." />
        <IndicadorCard etiqueta="Gastos" icono={TrendingDown} valor={totales.gastos} retraso={0.1}
          ayuda="Gastos del hogar y pagos de facturas del período." />
        <IndicadorCard etiqueta="Aportes recibidos" icono={PiggyBank} valor={totales.aportes} retraso={0.15}
          ayuda="Dinero que los integrantes entregaron al fondo común en el período." />
        <IndicadorCard etiqueta="Obligaciones pendientes" icono={FileWarning} valor={obligaciones.saldo_pendiente_total} retraso={0.2}
          ayuda="Lo que falta por pagar de facturas y deudas registradas."
          detalle={obligaciones.vencidas_cantidad > 0
            ? `${obligaciones.vencidas_cantidad} vencida(s): ${formatCOP(obligaciones.saldo_vencido)}`
            : `${obligaciones.pendientes_cantidad} pendiente(s)`} />
      </div>

      {/* Aviso de gastos sin regla de reparto */}
      {Number(data.gastos_sin_distribuir) > 0 && (
        <p role="status" className="rounded-xl bg-aviso/20 p-3 text-sm text-amber-900">
          Hay {formatCOP(data.gastos_sin_distribuir)} en gastos sin regla de reparto: no se cuentan en lo que cada integrante debe aportar.
        </p>
      )}

      {/* Gráficos */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Seccion titulo="Ingresos, aportes y gastos">
          <Suspense fallback={<Skeleton className="h-64" />}><GraficoIngresosGastos totales={totales} /></Suspense>
        </Seccion>
        <Seccion titulo="Gastos por categoría">
          <Suspense fallback={<Skeleton className="h-64" />}><GraficoCategorias categorias={data.gastos_por_categoria} /></Suspense>
        </Seccion>
      </div>

      {/* Paneles de detalle */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Seccion titulo="Próximos vencimientos"><PanelVencimientos vencimientos={data.proximos_vencimientos} /></Seccion>
        <Seccion titulo="Estado de los aportes"><PanelAportes integrantes={data.aportes} /></Seccion>
        <Seccion titulo="Cuentas"><PanelCuentas cuentas={data.cuentas} /></Seccion>
        <Seccion titulo="Préstamos activos">
          <div className="flex items-center gap-3">
            <HandCoins className="text-violeta" size={28} aria-hidden />
            <div>
              <p className="cifras text-xl font-extrabold text-morado">{formatCOP(prestamos.saldo_pendiente_total)}</p>
              <p className="text-sm text-texto-suave">
                {prestamos.activos_cantidad} préstamo(s) activo(s) · {prestamos.cuotas_pendientes_cantidad} cuota(s) pendiente(s)
              </p>
            </div>
          </div>
        </Seccion>
      </div>
    </section>
  );
}