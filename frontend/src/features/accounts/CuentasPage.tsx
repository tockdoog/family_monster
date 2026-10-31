// frontend/src/features/accounts/CuentasPage.tsx
// Pantalla de cuentas (ruta "/cuentas"): fondo común y fondos personales, con creación para administradores.

import { Plus } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { useIntegrantes } from "@/features/members/api";
import { ErrorApi } from "@/services/api/client";
import { useCuentas } from "./api";
import { CuentaCard } from "./components/CuentaCard";
import { FormularioCuenta } from "./components/FormularioCuenta";

/** Lista de cuentas con estados de carga, error y vacío. */
export function CuentasPage() {
  const { puede } = useAuth();
  const { data, isPending, isError, error, refetch, isFetching } = useCuentas();
  const integrantes = useIntegrantes();
  const [modalAbierto, setModalAbierto] = useState(false);
  // Solo oculta el botón: el backend rechaza la creación a quien no sea administrador.
  const puedeCrear = puede("gestionar_cuentas");

  // Carga: esqueletos con la forma final.
  if (isPending) {
    return (
      <div aria-busy className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-36" />)}
      </div>
    );
  }

  // Error con opción de reintentar.
  if (isError) {
    return (
      <Card role="alert">
        <p className="font-bold text-morado">No pudimos cargar las cuentas</p>
        <p className="mt-1 text-texto-suave">{error instanceof ErrorApi ? error.message : "Intenta de nuevo."}</p>
        <Button className="mt-4" cargando={isFetching} onClick={() => void refetch()}>Reintentar</Button>
      </Card>
    );
  }

  // Nombres de los dueños para mostrarlos en las tarjetas.
  const nombres = new Map((integrantes.data ?? []).map((i) => [i.id, i.nombre]));
  const comunes = data.filter((c) => c.es_fondo_comun);
  const personales = data.filter((c) => !c.es_fondo_comun);

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-morado">Cuentas</h1>
          <p className="text-texto-suave">Dónde está el dinero del hogar.</p>
        </div>
        {puedeCrear && (
          <Button onClick={() => setModalAbierto(true)}>
            <Plus size={20} aria-hidden /> Nueva cuenta
          </Button>
        )}
      </div>

      {data.length === 0 && (
        <EstadoVacio titulo="Aún no hay cuentas" texto="Crea una cuenta de efectivo o banco para empezar a registrar el dinero del hogar." />
      )}

      {comunes.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-extrabold text-morado">Fondo común</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{comunes.map((c) => <CuentaCard key={c.id} cuenta={c} />)}</div>
        </div>
      )}

      {personales.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-extrabold text-morado">Fondos personales</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {personales.map((c) => <CuentaCard key={c.id} cuenta={c} propietario={nombres.get(c.propietario_id ?? "")} />)}
          </div>
        </div>
      )}

      <Modal abierto={modalAbierto} titulo="Nueva cuenta" onCerrar={() => setModalAbierto(false)}>
        <FormularioCuenta onListo={() => setModalAbierto(false)} onCancelar={() => setModalAbierto(false)} />
      </Modal>
    </section>
  );
}