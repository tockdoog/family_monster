// frontend/src/services/auth/authApi.ts
// Llamadas de autenticación a /auth/login, /auth/logout y /auth/me.

import { api } from "@/services/api/client";
import type { Sesion } from "@/types/api";

/** Inicia sesión: el backend responde con la sesión y guarda la cookie HttpOnly. */
export const iniciarSesion = (email: string, contrasena: string) =>
  api.post<Sesion>("/auth/login", { email, contrasena });

/** Cierra la sesión: el backend borra la cookie. */
export const cerrarSesion = () => api.post<void>("/auth/logout");

/** Consulta quién tiene la sesión activa (lanza 401 si no hay). */
export const consultarSesion = (signal?: AbortSignal) => api.get<Sesion>("/auth/me", signal);