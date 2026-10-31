// frontend/src/features/obligations/ObligacionesPage.tsx
// Pantalla de obligaciones (ruta "/obligaciones"): facturas y deudas con filtro por estado, pago y anulación.

import { Plus } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCuentas } from "@/features/accounts/api";
import { useCategorias } from "@/features/categories/api";
import { useIntegrantes } from "@/features/members/api";
import { mensajeError } from "@/lib/errores";
import { LIMITE, useObligaciones } from "./api";
import { FormularioAnulacion } from "./components/FormularioAnulacion";
import { FormularioObligacion } from "./components/FormularioObligacion";
import { FormularioPago } from "./components/FormularioPago";
import { ObligacionCard } from "./components/ObligacionCard";
import { ETIQUETA_ESTADO, type Obligacion } from "./types";

/** Obligaciones con estados de carga, error y vacío. */
export function ObligacionesPage() {
  const { puede } = useAuth();
  const [estado, setEstado] = useState("");
  const [desplazamiento, setDesplazamiento] = useState(0);
  const [modalNueva, setModalNueva] = useState(false);
  const [aPagar, setAPagar] = useState<Obligacion | null>(null);
  const [aAnular, setAAnular] = useState<Obligacion | null>(null);
  const { data, isPending, isError, error, refetch, isFetching } = useObligaciones(estado, desplazamiento);
  const cuentas = useCuentas();
  const categorias = useCategorias();
  const integrantes = useIntegrantes();
  const nombresCategorias = new Map((categorias.data ?? []).map((c) => [c.id, c.nombre]));
  const nombresIntegrantes = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Obligaciones</h1>
          <p className="text-texto-suave">Facturas, servicios y deudas del hogar.</p>
        </div>
        {puede("gestionar_obligaciones") && <Button onClick={() => setModalNueva(true)}><Plus size={20} aria-hidden /> Nueva</Button>}
      </div>

      <Card>
        <Select etiqueta="Estado" value={estado} onChange={(e) => { setEstado(e.target.value); setDesplazamiento(0); }}>
          <option value="">Todas</option>
          {Object.entries(ETIQUETA_ESTADO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
      </Card>

      {isPending && <div aria-busy className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-52" />)}</div>}
      {isError && (
        <Card role="alert">
          <p className="font-bold text-morado">No pudimos cargar las obligaciones</p>
          <p className="mt-1 text-texto-suave">{mensajeError(error, "Intenta de nuevo.")}</p>
          <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
        </Card>
      )}
      {data && data.items.length === 0 && <EstadoVacio titulo="No hay obligaciones" texto="Registra las facturas y deudas del hogar para no olvidar ningún vencimiento." />}
      {data && data.items.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.items.map((o) => (
              <ObligacionCard key={o.id} obligacion={o} categorias={nombresCategorias} integrantes={nombresIntegrantes}
                puedePagar={puede("registrar_pagos")} puedeGestionar={puede("gestionar_obligaciones")} onPagar={setAPagar} onAnular={setAAnular} />
            ))}
          </div>
          <nav aria-label="Paginación" className="flex items-center justify-between gap-3">
            <Button variante="outline" disabled={desplazamiento === 0} onClick={() => setDesplazamiento(Math.max(0, desplazamiento - LIMITE))}>Anterior</Button>
            <p className="text-sm text-texto-suave">{desplazamiento + 1}–{desplazamiento + data.items.length} de {data.total}</p>
            <Button variante="outline" disabled={desplazamiento + LIMITE >= data.total} onClick={() => setDesplazamiento(desplazamiento + LIMITE)}>Siguiente</Button>
          </nav>
        </>
      )}

      <Modal abierto={modalNueva} titulo="Nueva obligación" onCerrar={() => setModalNueva(false)}>
        <FormularioObligacion onListo={() => setModalNueva(false)} onCancelar={() => setModalNueva(false)} />
      </Modal>
      <Modal abierto={aPagar !== null} titulo="Pagar obligación" onCerrar={() => setAPagar(null)}>
        {aPagar && <FormularioPago obligacion={aPagar} cuentas={cuentas.data ?? []} onListo={() => setAPagar(null)} onCancelar={() => setAPagar(null)} />}
      </Modal>
      <Modal abierto={aAnular !== null} titulo="Anular obligación" onCerrar={() => setAAnular(null)}>
        {aAnular && <FormularioAnulacion obligacion={aAnular} onListo={() => setAAnular(null)} onCancelar={() => setAAnular(null)} />}
      </Modal>
    </section>
  );
}