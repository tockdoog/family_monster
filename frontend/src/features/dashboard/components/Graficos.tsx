// frontend/src/features/dashboard/components/Graficos.tsx
// Gráficos con Recharts. Se cargan de forma diferida (lazy) para no pesar en la carga inicial.

import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { formatCOP } from "@/lib/formatCOP";
import type { GastoPorCategoria, TotalesPeriodo } from "../types";

// Tonos de la identidad morada para las series.
const PALETA = ["var(--color-violeta)", "var(--color-morado-secundario)", "var(--color-lavanda)", "var(--color-morado)", "#C4B5FD", "#8B5CF6"];

// Formato de montos en los tooltips de los gráficos.
const montoTooltip = (v: unknown) => formatCOP(Number(v));

/** Barras: ingresos, aportes y gastos del período (valores del backend, solo presentados). */
export function GraficoIngresosGastos({ totales }: { totales: TotalesPeriodo }) {
  const datos = [
    { nombre: "Ingresos", valor: Number(totales.ingresos) },
    { nombre: "Aportes", valor: Number(totales.aportes) },
    { nombre: "Gastos", valor: Number(totales.gastos) },
  ];
  if (datos.every((d) => d.valor === 0)) {
    return <EstadoVacio titulo="Aún no hay movimientos" texto="Cuando registres ingresos o gastos del mes, los verás comparados aquí." />;
  }
  return (
    <div role="img" aria-label="Gráfico de barras de ingresos, aportes y gastos del período" className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos}>
          <XAxis dataKey="nombre" tickLine={false} />
          <YAxis hide />
          <Tooltip formatter={montoTooltip} />
          <Bar dataKey="valor" radius={[8, 8, 0, 0]}>
            {datos.map((d, i) => (
              <Cell key={d.nombre} fill={PALETA[i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Dona de gastos por categoría, con lista de montos debajo para que no dependa solo del color. */
export function GraficoCategorias({ categorias }: { categorias: GastoPorCategoria[] }) {
  const datos = categorias.map((c) => ({ nombre: c.categoria, valor: Number(c.importe) }));
  if (datos.length === 0) {
    return <EstadoVacio titulo="Sin gastos este mes" texto="Aquí verás en qué categorías se va el dinero del hogar." />;
  }
  return (
    <div>
      <div role="img" aria-label="Gráfico de dona de gastos por categoría" className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={datos} dataKey="valor" nameKey="nombre" innerRadius={55} outerRadius={90} paddingAngle={2}>
              {datos.map((d, i) => (
                <Cell key={d.nombre} fill={PALETA[i % PALETA.length]} />
              ))}
            </Pie>
            <Tooltip formatter={montoTooltip} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1 text-sm">
        {datos.map((d, i) => (
          <li key={d.nombre} className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <span aria-hidden className="size-3 rounded-full" style={{ background: PALETA[i % PALETA.length] }} />
              {d.nombre}
            </span>
            <span className="cifras font-semibold">{formatCOP(d.valor)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}