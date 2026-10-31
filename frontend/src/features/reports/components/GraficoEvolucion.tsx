// frontend/src/features/reports/components/GraficoEvolucion.tsx
// Evolución de ingresos, aportes y gastos por mes. Se carga de forma diferida (lazy).

import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCOP } from "@/lib/formatCOP";

/** Un punto por mes con los totales ya calculados por el backend. */
export interface PuntoMes {
  mes: string;
  ingresos: number;
  aportes: number;
  gastos: number;
}

/** Barras agrupadas por mes. */
export default function GraficoEvolucion({ datos }: { datos: PuntoMes[] }) {
  return (
    <div role="img" aria-label="Gráfico de barras con la evolución mensual de ingresos, aportes y gastos" className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos}>
          <XAxis dataKey="mes" tickLine={false} />
          <YAxis hide />
          <Tooltip formatter={(v) => formatCOP(Number(v))} />
          <Legend />
          <Bar dataKey="ingresos" name="Ingresos" fill="var(--color-violeta)" radius={[6, 6, 0, 0]} />
          <Bar dataKey="aportes" name="Aportes" fill="var(--color-lavanda)" radius={[6, 6, 0, 0]} />
          <Bar dataKey="gastos" name="Gastos" fill="var(--color-morado-secundario)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}