# backend/index.py
# Archivo de entrada para Vercel: expone la aplicación FastAPI con el nombre "app" en un lugar
# que Vercel reconoce sin configuración adicional (raíz del proyecto, archivo index.py).

from app.main import app  # noqa: F401  (Vercel busca la variable "app" en este archivo)