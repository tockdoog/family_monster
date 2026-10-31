// frontend/src/features/loans/PrestamosPage.tsx
// Pantalla de préstamos (ruta "/prestamos"): listado con filtro, alta, pago de cuotas y detalle.

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
import { useIntegrantes } from "@/features/members/api";
import { mensajeError } from "@/lib/errores";
import { LIMITE, usePrestamos } from "./api";
import { DetallePrestamo } from "./components/DetallePrestamo";
import { FormularioPagoCuota } from "./components/FormularioPagoCuota";
import { FormularioPrestamo } from "./components/FormularioPrestamo";
import { PrestamoCard } from "./components/PrestamoCard";
import { ETIQUETA_ESTADO_PRESTAMO, type Prestamo } from "./types";

/** Préstamos con estados de carga, error y vacío. */
export function PrestamosPage() {
  const { puede } = useAuth();
  const [estado, setEstado] = useState("");
  const [desplazamiento, setDesplazamiento] = useState(0);
  const [modalNuevo, setModalNuevo] = useState(false);
  const [aPagar, setAPagar] = useState<Prestamo | null>(null);
  const [verDetalle, setVerDetalle] = useState<Prestamo | null>(null);
  const { data, isPending, isError, error, refetch, isFetching } = usePrestamos(estado, desplazamiento);
  const cuentas = useCuentas();
  const integrantes = useIntegrantes();
  const nombres = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Préstamos</h1>
          <p className="text-texto-suave">Dinero prestado y cuotas pendientes.</p>
        </div>
        {puede("gestionar_prestamos") && <Button onClick={() => setModalNuevo(true)}><Plus size={20} aria-hidden /> Nuevo</Button>}
      </div>

      <Card>
        <Select etiqueta="Estado" value={estado} onChange={(e) => { setEstado(e.target.value); setDesplazamiento(0); }}>
          <option value="">Todos</option>
          {Object.entries(ETIQUETA_ESTADO_PRESTAMO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
      </Card>

      {isPending && <div aria-busy className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-56" />)}</div>}
      {isError && (
        <Card role="alert">
          <p className="font-bold text-morado">No pudimos cargar los préstamos</p>
          <p className="mt-1 text-texto-suave">{mensajeError(error, "Intenta de nuevo.")}</p>
          <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
        </Card>
      )}
      {data && data.items.length === 0 && <EstadoVacio titulo="No hay préstamos" texto="Cuando registres un préstamo verás aquí su saldo, sus cuotas y su progreso." />}
      {data && data.items.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.items.map((p) => <PrestamoCard key={p.id} prestamo={p} integrantes={nombres} puedePagar={puede("registrar_pagos")} onPagar={setAPagar} onDetalle={setVerDetalle} />)}
          </div>
          <nav aria-label="Paginación" className="flex items-center justify-between gap-3">
            <Button variante="outline" disabled={desplazamiento === 0} onClick={() => setDesplazamiento(Math.max(0, desplazamiento - LIMITE))}>Anterior</Button>
            <p className="text-sm text-texto-suave">{desplazamiento + 1}–{desplazamiento + data.items.length} de {data.total}</p>
            <Button variante="outline" disabled={desplazamiento + LIMITE >= data.total} onClick={() => setDesplazamiento(desplazamiento + LIMITE)}>Siguiente</Button>
          </nav>
        </>
      )}

      <Modal abierto={modalNuevo} titulo="Nuevo préstamo" onCerrar={() => setModalNuevo(false)}>
        <FormularioPrestamo integrantes={integrantes.data ?? []} cuentas={cuentas.data ?? []} onListo={() => setModalNuevo(false)} onCancelar={() => setModalNuevo(false)} />
      </Modal>
      <Modal abierto={aPagar !== null} titulo="Pagar cuota" onCerrar={() => setAPagar(null)}>
        {aPagar && <FormularioPagoCuota prestamo={aPagar} cuentas={cuentas.data ?? []} onListo={() => setAPagar(null)} onCancelar={() => setAPagar(null)} />}
      </Modal>
      <Modal abierto={verDetalle !== null} titulo="Detalle del préstamo" onCerrar={() => setVerDetalle(null)}>
        {verDetalle && <DetallePrestamo id={verDetalle.id} />}
      </Modal>
    </section>
  );
}