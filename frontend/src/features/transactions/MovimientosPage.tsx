// frontend/src/features/transactions/MovimientosPage.tsx
// Pantalla de movimientos (ruta "/movimientos"): filtros, listado paginado, registro y reversión.

import { Plus } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCuentas } from "@/features/accounts/api";
import { useCategorias } from "@/features/categories/api";
import { useIntegrantes } from "@/features/members/api";
import { ErrorApi } from "@/services/api/client";
import { LIMITE, useMovimientos } from "./api";
import { Filtros } from "./components/FiltrosMovimientos";
import { FormularioMovimiento } from "./components/FormularioMovimiento";
import { FormularioReversion } from "./components/FormularioReversion";
import { MovimientoItem } from "./components/MovimientoItem";
import { FILTROS_VACIOS, type FiltrosMovimientos, type Movimiento } from "./types";

/** Historial financiero con estados de carga, error y vacío. */
export function MovimientosPage() {
  const { puede } = useAuth();
  const [filtros, setFiltros] = useState<FiltrosMovimientos>(FILTROS_VACIOS);
  const [desplazamiento, setDesplazamiento] = useState(0);
  const [modalNuevo, setModalNuevo] = useState(false);
  const [aRevertir, setARevertir] = useState<Movimiento | null>(null);
  const { data, isPending, isError, error, refetch, isFetching } = useMovimientos(filtros, desplazamiento);
  const cuentas = useCuentas();
  const categorias = useCategorias();
  const integrantes = useIntegrantes();

  // Nombres para mostrar en lugar de identificadores.
  const nombresCuentas = new Map((cuentas.data ?? []).map((c) => [c.id, c.nombre]));
  const nombresCategorias = new Map((categorias.data ?? []).map((c) => [c.id, c.nombre]));
  const nombresIntegrantes = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));

  // Cambiar un filtro vuelve a la primera página.
  const cambiarFiltros = (f: FiltrosMovimientos) => { setFiltros(f); setDesplazamiento(0); };

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Movimientos</h1>
          <p className="text-texto-suave">Ingresos, gastos y transferencias del hogar.</p>
        </div>
        {/* Solo oculta el botón: el backend valida el permiso al registrar */}
        {puede("registrar_movimientos") && (
          <Button onClick={() => setModalNuevo(true)}><Plus size={20} aria-hidden /> Registrar</Button>
        )}
      </div>

      <Card><Filtros valor={filtros} cuentas={cuentas.data ?? []} onCambio={cambiarFiltros} /></Card>

      {isPending && <div aria-busy className="space-y-3">{Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div>}

      {isError && (
        <Card role="alert">
          <p className="font-bold text-morado">No pudimos cargar los movimientos</p>
          <p className="mt-1 text-texto-suave">{error instanceof ErrorApi ? error.message : "Intenta de nuevo."}</p>
          <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
        </Card>
      )}

      {data && data.items.length === 0 && <EstadoVacio titulo="No hay movimientos" texto="Cuando registres ingresos o gastos, o cambies los filtros, los verás aquí." />}

      {data && data.items.length > 0 && (
        <>
          <ul className="space-y-3">
            {data.items.map((m) => (
              <MovimientoItem key={m.id} movimiento={m} cuentas={nombresCuentas} categorias={nombresCategorias} integrantes={nombresIntegrantes}
                puedeRevertir={puede("revertir_movimientos")} onRevertir={setARevertir} />
            ))}
          </ul>
          <nav aria-label="Paginación" className="flex items-center justify-between gap-3">
            <Button variante="outline" disabled={desplazamiento === 0} onClick={() => setDesplazamiento(Math.max(0, desplazamiento - LIMITE))}>Anterior</Button>
            <p className="text-sm text-texto-suave">{desplazamiento + 1}–{desplazamiento + data.items.length} de {data.total}</p>
            <Button variante="outline" disabled={desplazamiento + LIMITE >= data.total} onClick={() => setDesplazamiento(desplazamiento + LIMITE)}>Siguiente</Button>
          </nav>
        </>
      )}

      <Modal abierto={modalNuevo} titulo="Registrar movimiento" onCerrar={() => setModalNuevo(false)}>
        <FormularioMovimiento onListo={() => setModalNuevo(false)} onCancelar={() => setModalNuevo(false)} />
      </Modal>
      <Modal abierto={aRevertir !== null} titulo="Revertir movimiento" onCerrar={() => setARevertir(null)}>
        {aRevertir && <FormularioReversion movimiento={aRevertir} onListo={() => setARevertir(null)} onCancelar={() => setARevertir(null)} />}
      </Modal>
    </section>
  );
}