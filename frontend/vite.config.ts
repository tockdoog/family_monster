// frontend/vite.config.ts
// Configuración de Vite: React, Tailwind, alias "@" y proxy local hacia el backend FastAPI.

import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  // Plugins: React (JSX) y Tailwind v4.
  plugins: [react(), tailwindcss()],

  // Alias para importar con "@/ruta" en lugar de rutas relativas largas.
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },

  // En desarrollo, /api se reenvía al backend local: mismo origen, la cookie de sesión funciona sin CORS.
  server: { port: 5173, proxy: { "/api": { target: "http://localhost:8000", changeOrigin: false } } },

  // Configuración de pruebas (Vitest).
  test: { environment: "jsdom", globals: true },
});