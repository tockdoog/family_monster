// frontend/src/features/contributions/AportesPage.tsx
// Pantalla de aportes (ruta "/aportes"): quién debe, quién ha puesto, reglas y registro de aportes/reembolsos.

import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCuentas } from "@/features/accounts/api";
import { useIntegrantes } from "@/features/members/api";
import { formatCOP } from "@/lib/formatCOP";
import { formatFechaCorta } from "@/lib/fechas";
import { mensajeError } from "@/lib/errores";
import type { ResumenIntegrante } from "@/types/finanzas";
import { useReglas, useResumenAportes } from "./api";
import { FormularioFondos } from "./components/FormularioFondos";
import { ListaReglas } from "./components/ListaReglas";
import { TarjetaIntegrante } from "./components/TarjetaIntegrante";
import type { ModoFondos } from "./schemas";

/** Aportes del período con estados de carga, error y vacío. */
export function AportesPage() {
  const { puede } = useAuth();
  const resumen = useResumenAportes();
  const reglas = useReglas();
  const integrantes = useIntegrantes();
  const cuentas = useCuentas();
  const [modal, setModal] = useState<{ modo: ModoFondos; inicial?: { integranteId: string; importe: string } } | null>(null);
  const puedeRegistrar = puede("registrar_movimientos");
  const nombres = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));

  if (resumen.isPending) return <div aria-busy className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-48" />)}</div>;
  if (resumen.isError) {
    return (
      <Card role="alert">
        <p className="font-bold text-morado">No pudimos cargar los aportes</p>
        <p className="mt-1 text-texto-suave">{mensajeError(resumen.error, "Intenta de nuevo.")}</p>
        <Button className="mt-4" cargando={resumen.isFetching} onClick={() => void resumen.refetch()}>Reintentar</Button>
      </Card>
    );
  }
  const d = resumen.data;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Aportes</h1>
          <p className="text-texto-suave">Del {formatFechaCorta(d.desde)} al {formatFechaCorta(d.hasta)}</p>
        </div>
        {puedeRegistrar && (
          <div className="flex gap-2">
            <Button onClick={() => setModal({ modo: "aporte" })}>Registrar aporte</Button>
            <Button variante="outline" onClick={() => setModal({ modo: "reembolso" })}>Reembolso</Button>
          </div>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card><p className="text-sm font-semibold text-morado-secundario">Total esperado</p><p className="cifras text-2xl font-extrabold text-morado">{formatCOP(d.total_esperado)}</p></Card>
        <Card><p className="text-sm font-semibold text-morado-secundario">Total aportado</p><p className="cifras text-2xl font-extrabold text-morado">{formatCOP(d.total_aportado_neto)}</p></Card>
      </div>
      {Number(d.gastos_sin_distribuir) > 0 && (
        <p role="status" className="rounded-xl bg-aviso/20 p-3 text-sm text-amber-900">Hay {formatCOP(d.gastos_sin_distribuir)} en gastos sin regla de reparto: no se cuentan en lo esperado.</p>
      )}

      {d.integrantes.length === 0
        ? <EstadoVacio titulo="Sin integrantes con aportes" texto="Cuando exista una regla de reparto verás aquí cómo va cada integrante." />
        : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {d.integrantes.map((i) => (
              <TarjetaIntegrante key={i.integrante_id} integrante={i} puedeReembolsar={puedeRegistrar}
                onReembolsar={(x: ResumenIntegrante) => setModal({ modo: "reembolso", inicial: { integranteId: x.integrante_id, importe: x.reembolso_pendiente } })} />
            ))}
          </div>}

      <Card>
        <h2 className="mb-3 text-lg font-extrabold text-morado">Reglas de reparto</h2>
        {reglas.isPending ? <Skeleton className="h-24" /> : reglas.isError
          ? <p role="alert" className="text-texto-suave">{mensajeError(reglas.error, "No pudimos cargar las reglas.")}</p>
          : <ListaReglas reglas={reglas.data} nombres={nombres} />}
      </Card>

      <Modal abierto={modal !== null} titulo={modal?.modo === "reembolso" ? "Registrar reembolso" : "Registrar aporte"} onCerrar={() => setModal(null)}>
        {modal && <FormularioFondos modo={modal.modo} inicial={modal.inicial} integrantes={integrantes.data ?? []} cuentas={cuentas.data ?? []}
          onListo={() => setModal(null)} onCancelar={() => setModal(null)} />}
      </Modal>
    </section>
  );
}