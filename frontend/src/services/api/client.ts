// frontend/src/services/api/client.ts
// Cliente HTTP único. La sesión viaja en una cookie HttpOnly: el frontend nunca toca el token.

// Ruta base de la API (relativa: la atiende el proxy de Vite o el rewrite de Vercel).
const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

/** Error de la API con mensaje apto para mostrar al usuario. */
export class ErrorApi extends Error {
  constructor(
    public readonly estado: number,
    public readonly codigo: string,
    mensaje: string,
    public readonly detalle?: unknown,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }
}

// Función que se ejecuta cuando la sesión vence (401). La registra el proveedor de autenticación.
let alSesionExpirada: (() => void) | null = null;

/** Registra qué hacer cuando el backend responde 401. */
export function registrarSesionExpirada(manejador: (() => void) | null): void {
  alSesionExpirada = manejador;
}

/** Genera una clave para que reintentos de un mismo envío no dupliquen la operación. */
export function crearClaveIdempotencia(): string {
  return crypto.randomUUID();
}

// Mensajes seguros por estado, usados cuando el backend no entrega uno legible.
const MENSAJES: Record<number, string> = {
  401: "Tu sesión venció. Inicia sesión de nuevo.",
  403: "No tienes permiso para realizar esta acción.",
  404: "No encontramos lo que buscas.",
  422: "Revisa los datos ingresados.",
  429: "Demasiados intentos. Espera un momento.",
};

/** Extrae código y mensaje del cuerpo de error (formato por confirmar con exceptions.py). */
function leerError(estado: number, cuerpo: unknown): ErrorApi {
  const c = (cuerpo ?? {}) as Record<string, unknown>;
  const anidado = (c.error ?? c) as Record<string, unknown>;
  const mensaje = typeof anidado.mensaje === "string" ? anidado.mensaje : undefined;
  const codigo = typeof anidado.codigo === "string" ? anidado.codigo : "error";
  return new ErrorApi(
    estado,
    codigo,
    mensaje ?? MENSAJES[estado] ?? "Ocurrió un error inesperado. Intenta de nuevo.",
    anidado.detalle,
  );
}

interface OpcionesPeticion {
  cuerpo?: unknown;
  idempotencia?: string;
  signal?: AbortSignal;
}

/** Ejecuta una petición JSON y devuelve el cuerpo tipado (o undefined en 204). */
async function peticion<T>(metodo: string, ruta: string, op: OpcionesPeticion = {}): Promise<T> {
  const cabeceras: Record<string, string> = { Accept: "application/json" };
  if (op.cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";
  if (op.idempotencia) cabeceras["Idempotency-Key"] = op.idempotencia;

  let respuesta: Response;
  try {
    respuesta = await fetch(`${BASE_URL}${ruta}`, {
      method: metodo,
      headers: cabeceras,
      credentials: "include",
      body: op.cuerpo !== undefined ? JSON.stringify(op.cuerpo) : undefined,
      signal: op.signal,
    });
  } catch {
    throw new ErrorApi(0, "sin_conexion", "No hay conexión con el servidor. Revisa tu internet.");
  }

  if (respuesta.status === 204) return undefined as T;
  const cuerpo: unknown = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    // Un 401 en /auth/login es "credenciales incorrectas", no sesión vencida.
    if (respuesta.status === 401 && !ruta.startsWith("/auth/login")) alSesionExpirada?.();
    throw leerError(respuesta.status, cuerpo);
  }
  return cuerpo as T;
}

// API pública del cliente: un método por verbo HTTP.
export const api = {
  get: <T>(ruta: string, signal?: AbortSignal) => peticion<T>("GET", ruta, { signal }),
  post: <T>(ruta: string, cuerpo?: unknown, idempotencia?: string) =>
    peticion<T>("POST", ruta, { cuerpo, idempotencia }),
  put: <T>(ruta: string, cuerpo?: unknown) => peticion<T>("PUT", ruta, { cuerpo }),
  patch: <T>(ruta: string, cuerpo?: unknown) => peticion<T>("PATCH", ruta, { cuerpo }),
  delete: <T>(ruta: string) => peticion<T>("DELETE", ruta),
};