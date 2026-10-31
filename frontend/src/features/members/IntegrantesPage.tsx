// frontend/src/features/members/IntegrantesPage.tsx
// Pantalla de integrantes (ruta "/integrantes"): quiénes forman el hogar y quién tiene acceso.

import { Plus } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { mensajeError } from "@/lib/errores";
import { useIntegrantes } from "./api";
import { FormularioAcceso } from "./components/FormularioAcceso";
import { FormularioIntegrante } from "./components/FormularioIntegrante";
import { IntegranteCard } from "./components/IntegranteCard";
import type { Integrante } from "./types";

/** Integrantes con estados de carga, error y vacío. */
export function IntegrantesPage() {
  const { puede } = useAuth();
  const { data, isPending, isError, error, refetch, isFetching } = useIntegrantes();
  const [modalNuevo, setModalNuevo] = useState(false);
  const [conAcceso, setConAcceso] = useState<Integrante | null>(null);
  const puedeGestionar = puede("gestionar_integrantes");

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Integrantes</h1>
          <p className="text-texto-suave">Las personas que forman el hogar.</p>
        </div>
        {puedeGestionar && <Button onClick={() => setModalNuevo(true)}><Plus size={20} aria-hidden /> Nuevo</Button>}
      </div>

      {isPending && <div aria-busy className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-28" />)}</div>}
      {isError && (
        <Card role="alert">
          <p className="font-bold text-morado">No pudimos cargar los integrantes</p>
          <p className="mt-1 text-texto-suave">{mensajeError(error, "Intenta de nuevo.")}</p>
          <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
        </Card>
      )}
      {data && data.length === 0 && <EstadoVacio titulo="Aún no hay integrantes" texto="Registra a las personas del hogar para repartir gastos y aportes." />}
      {data && data.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.map((i) => <IntegranteCard key={i.id} integrante={i} puedeGestionar={puedeGestionar} onAcceso={setConAcceso} />)}
        </div>
      )}

      <Modal abierto={modalNuevo} titulo="Nuevo integrante" onCerrar={() => setModalNuevo(false)}>
        <FormularioIntegrante onListo={() => setModalNuevo(false)} onCancelar={() => setModalNuevo(false)} />
      </Modal>
      <Modal abierto={conAcceso !== null} titulo="Dar acceso a la aplicación" onCerrar={() => setConAcceso(null)}>
        {conAcceso && <FormularioAcceso integrante={conAcceso} onListo={() => setConAcceso(null)} onCancelar={() => setConAcceso(null)} />}
      </Modal>
    </section>
  );
}