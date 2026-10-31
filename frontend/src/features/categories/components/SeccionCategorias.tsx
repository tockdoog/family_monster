// frontend/src/features/categories/components/SeccionCategorias.tsx
// Gestión de categorías dentro de Configuración: ver, crear, renombrar y activar/desactivar.

import { Plus } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/app/providers/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { mensajeError } from "@/lib/errores";
import { useActualizarCategoria, useCategorias, type Categoria } from "../api";
import { FormularioCategoria } from "./FormularioCategoria";

/** Lista de categorías; desactivar es reversible y no borra el historial. */
export function SeccionCategorias() {
  const { puede } = useAuth();
  const { data, isPending, isError, error, refetch } = useCategorias();
  const actualizar = useActualizarCategoria();
  const [modal, setModal] = useState<{ categoria?: Categoria } | null>(null);
  const [errorCambio, setErrorCambio] = useState<string | null>(null);
  const puedeGestionar = puede("gestionar_categorias");

  // Activa o desactiva una categoría y muestra el error del backend si lo hay.
  const alternar = async (c: Categoria) => {
    setErrorCambio(null);
    try { await actualizar.mutateAsync({ id: c.id, cambios: { activa: !c.activa } }); } catch (e) { setErrorCambio(mensajeError(e, "No pudimos cambiar el estado.")); }
  };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-extrabold text-morado">Categorías</h2>
          <p className="text-sm text-texto-suave">Las categorías inactivas no se pueden elegir en registros nuevos, pero conservan su historial.</p>
        </div>
        {puedeGestionar && <Button variante="outline" onClick={() => setModal({})}><Plus size={18} aria-hidden /> Nueva</Button>}
      </div>
      {errorCambio && <p role="alert" className="mb-3 rounded-xl bg-alerta/10 p-3 text-sm text-red-800">{errorCambio}</p>}
      {isPending && <Skeleton className="h-32" />}
      {isError && <p role="alert" className="text-texto-suave">{mensajeError(error, "No pudimos cargar las categorías.")} <button type="button" className="font-semibold text-violeta underline" onClick={() => void refetch()}>Reintentar</button></p>}
      {data && data.length === 0 && <EstadoVacio titulo="Sin categorías" texto="Crea categorías para clasificar los gastos del hogar." />}
      {data && data.length > 0 && (
        <ul className="divide-y divide-lavanda/30">
          {data.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <span className="flex items-center gap-2 font-semibold">{c.nombre} <Badge tono={c.activa ? "exito" : "neutro"}>{c.activa ? "Activa" : "Inactiva"}</Badge></span>
              {puedeGestionar && (
                <span className="flex gap-1">
                  <Button variante="ghost" onClick={() => setModal({ categoria: c })} aria-label={`Renombrar ${c.nombre}`}>Renombrar</Button>
                  <Button variante="ghost" cargando={actualizar.isPending && actualizar.variables?.id === c.id} onClick={() => void alternar(c)}>{c.activa ? "Desactivar" : "Activar"}</Button>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      <Modal abierto={modal !== null} titulo={modal?.categoria ? "Renombrar categoría" : "Nueva categoría"} onCerrar={() => setModal(null)}>
        {modal && <FormularioCategoria categoria={modal.categoria} onListo={() => setModal(null)} onCancelar={() => setModal(null)} />}
      </Modal>
    </Card>
  );
}