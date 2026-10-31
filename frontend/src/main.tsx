// frontend/src/main.tsx
// Punto de entrada: monta React y carga los estilos globales.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "@/app/App";
import "@/styles/globals.css";

// Monta la aplicación en el elemento #root de index.html.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);