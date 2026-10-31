// frontend/src/features/reports/InformesPage.tsx
// Pantalla de informes (ruta "/informes"): resumen del mes, gráficos, evolución y exportación a CSV.

import { Download } from "lucide-react";
import { Suspense, lazy, useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Ayuda } from "@/components/ui/Ayuda";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCuentas } from "@/features/accounts/api";
import { useCategorias } from "@/features/categories/api";
import { useIntegrantes } from "@/features/members/api";
import { MovimientoItem } from "@/features/transactions/components/MovimientoItem";
import { formatCOP } from "@/lib/formatCOP";
import { mensajeError } from "@/lib/errores";
import { descargarInformeCsv, useEvolucion, useInformeMensual } from "./api";
import type { PuntoMes } from "./components/GraficoEvolucion";
import { etiquetaMes, mesActual, ultimosMeses } from "./meses";

// Los gráficos (Recharts) se descargan solo cuando se necesitan.
const GraficoIngresosGastos = lazy(() => import("@/features/dashboard/components/Graficos").then((m) => ({ default: m.GraficoIngresosGastos })));
const GraficoCategorias = lazy(() => import("@/features/dashboard/components/Graficos").then((m) => ({ default: m.GraficoCategorias })));
const GraficoEvolucion = lazy(() => import("./components/GraficoEvolucion"));

// Cantidad de movimientos que se muestran por tanda en pantalla.
const TANDA = 25;
const MESES_EVOLUCION = 6;

/** Informe mensual con estados de carga, error y vacío. */
export function InformesPage() {
  const { puede } = useAuth();
  const [mes, setMes] = useState(mesActual());
  const [visibles, setVisibles] = useState(TANDA);
  const [exportando, setExportando] = useState(false);
  const [errorExportar, setErrorExportar] = useState<string | null>(null);
  const informe = useInformeMensual(mes);
  const evolucion = useEvolucion(ultimosMeses(mes, MESES_EVOLUCION));
  const cuentas = useCuentas();
  const categorias = useCategorias();
  const integrantes = useIntegrantes();
  const nombresCuentas = new Map((cuentas.data ?? []).map((c) => [c.id, c.nombre]));
  const nombresCategorias = new Map((categorias.data ?? []).map((c) => [c.id, c.nombre]));
  const nombresIntegrantes = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));

  // Cambia de mes y reinicia la lista de movimientos visibles.
  const cambiarMes = (valor: string) => { if (/^20\d{2}-(0[1-9]|1[0-2])$/.test(valor)) { setMes(valor); setVisibles(TANDA); } };

  // Descarga el CSV; los errores (por ejemplo, sin permiso) se muestran al usuario.
  const exportar = async () => {
    setExportando(true);
    setErrorExportar(null);
    try { await descargarInformeCsv(mes); } catch (e) { setErrorExportar(mensajeError(e, "No pudimos exportar el informe.")); } finally { setExportando(false); }
  };

  // Datos de la evolución: solo cuando todos los meses llegaron bien.
  const meses = ultimosMeses(mes, MESES_EVOLUCION);
  const evolucionLista = evolucion.every((r) => r.isSuccess);
  const puntos: PuntoMes[] = evolucionLista
    ? evolucion.map((r, i) => ({ mes: etiquetaMes(meses[i]), ingresos: Number(r.data?.totales.ingresos), aportes: Number(r.data?.totales.aportes), gastos: Number(r.data?.totales.gastos) }))
    : [];

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Informes</h1>
          <p className="text-texto-suave">Cómo le fue al hogar en {etiquetaMes(mes)}.</p>
        </div>
        <div className="flex items-end gap-3">
          <Input etiqueta="Mes" type="month" value={mes} max={mesActual()} onChange={(e) => cambiarMes(e.target.value)} />
          {puede("exportar_informes") && (
            <Button variante="outline" cargando={exportando} onClick={() => void exportar()}><Download size={18} aria-hidden /> Exportar CSV</Button>
          )}
        </div>
      </div>
      {errorExportar && <p role="alert" className="rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorExportar}</p>}

      {informe.isPending && <div aria-busy className="space-y-4"><Skeleton className="h-28" /><Skeleton className="h-72" /></div>}
      {informe.isError && (
        <Card role="alert">
          <p className="font-bold text-morado">No pudimos cargar el informe</p>
          <p className="mt-1 text-texto-suave">{mensajeError(informe.error, "Intenta de nuevo.")}</p>
          <Button className="mt-4" cargando={informe.isFetching} onClick={() => void informe.refetch()}>Reintentar</Button>
        </Card>
      )}

      {informe.data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {([
              ["Ingresos", informe.data.totales.ingresos, "Sueldos, ventas u otros ingresos. No incluye aportes ni préstamos."],
              ["Aportes", informe.data.totales.aportes, "Dinero que los integrantes entregaron al fondo común."],
              ["Gastos", informe.data.totales.gastos, "Gastos del hogar y pagos de facturas."],
              ["Pagos de préstamos", informe.data.totales.pagos_de_prestamos, "Cuotas de préstamos pagadas. No se cuentan como gasto ordinario."],
              ["Balance del mes", informe.data.totales.balance_operativo, "Ingresos más aportes, menos gastos. No incluye préstamos ni transferencias."],
            ] as const).map(([titulo, valor, ayuda]) => (
              <Card key={titulo}>
                <p className="flex items-center gap-1 text-sm font-semibold text-morado-secundario">{titulo}<Ayuda texto={ayuda} /></p>
                <p className="cifras mt-1 text-2xl font-extrabold text-morado">{formatCOP(valor)}</p>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card><h2 className="mb-3 text-lg font-extrabold text-morado">Ingresos, aportes y gastos</h2><Suspense fallback={<Skeleton className="h-64" />}><GraficoIngresosGastos totales={informe.data.totales} /></Suspense></Card>
            <Card><h2 className="mb-3 text-lg font-extrabold text-morado">Gastos por categoría</h2><Suspense fallback={<Skeleton className="h-64" />}><GraficoCategorias categorias={informe.data.gastos_por_categoria} /></Suspense></Card>
          </div>

          <Card>
            <h2 className="mb-3 text-lg font-extrabold text-morado">Evolución de los últimos {MESES_EVOLUCION} meses</h2>
            {evolucion.some((r) => r.isError) ? <p role="alert" className="text-texto-suave">No pudimos cargar la evolución de algunos meses.</p>
              : !evolucionLista ? <Skeleton className="h-72" />
              : <Suspense fallback={<Skeleton className="h-72" />}><GraficoEvolucion datos={puntos} /></Suspense>}
          </Card>

          <div className="space-y-3">
            <h2 className="text-lg font-extrabold text-morado">Movimientos del mes ({informe.data.total_movimientos})</h2>
            {informe.data.truncado && <p role="status" className="rounded-xl bg-aviso/20 p-3 text-sm text-amber-900">El mes tiene más movimientos de los que se incluyen en el informe.</p>}
            {informe.data.movimientos.length === 0 ? <EstadoVacio titulo="Sin movimientos" texto="No hubo movimientos en este mes." /> : (
              <>
                <ul className="space-y-3">
                  {informe.data.movimientos.slice(0, visibles).map((m) => (
                    <MovimientoItem key={m.id} movimiento={m} cuentas={nombresCuentas} categorias={nombresCategorias} integrantes={nombresIntegrantes} puedeRevertir={false} onRevertir={() => undefined} />
                  ))}
                </ul>
                {visibles < informe.data.movimientos.length && <Button variante="outline" onClick={() => setVisibles(visibles + TANDA)}>Ver más movimientos</Button>}
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}