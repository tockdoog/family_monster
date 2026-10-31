<!-- frontend/README.md -->
# Familia Monster — Frontend

Aplicación web privada para administrar las finanzas de un hogar familiar: dinero disponible, movimientos, aportes, facturas, préstamos e informes. Todo en español y en pesos colombianos (COP).

El frontend **solo presenta y captura datos**. El backend (FastAPI + PostgreSQL en Neon) es la autoridad para saldos, reglas, permisos y validaciones. Nunca se calcula un saldo oficial en React.

---

## 1. Tecnologías

| Área | Herramienta |
|---|---|
| Base | React 19, TypeScript (modo estricto), Vite 6 |
| Estilos | Tailwind CSS 4 con tokens en `src/styles/theme.css` |
| Rutas | React Router 7 |
| Datos del servidor | TanStack Query 5 |
| Formularios | React Hook Form + Zod |
| Gráficos | Recharts 3 (carga diferida) |
| Animaciones | Motion (respeta `prefers-reduced-motion`) |
| Íconos | Lucide React |
| Pruebas | Vitest + React Testing Library + jsdom |
| Despliegue | Vercel (frontend) + Neon (PostgreSQL del backend) |

---

## 2. Puesta en marcha local

Requisitos: Node.js 20 o superior y el backend corriendo en `http://localhost:8000`.

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con recarga |
| `npm run build` | Revisa tipos (`tsc --noEmit`) y compila a `dist/` |
| `npm run preview` | Sirve la compilación para revisarla |
| `npm test` | Ejecuta todas las pruebas una vez |

**Backend local:** desde `backend/`, `uvicorn app.main:app --port 8000`. El proxy de Vite reenvía `/api` a ese puerto, así la cookie de sesión funciona sin CORS. Si el navegador no guarda la cookie (pasa en Safari sobre `http://localhost`), pon `COOKIE_SECURE=false` en el `.env` **local** del backend. En producción debe ser `true`.

---

## 3. Variables de entorno

Archivo de ejemplo: `.env.example`. Copiar como `.env.local`.

| Variable | Valor | Nota |
|---|---|---|
| `VITE_API_URL` | `/api/v1` | Ruta **relativa** a propósito (ver sección 6) |

Todo lo que empieza con `VITE_` queda visible en el navegador. **Nunca** poner contraseñas, tokens ni la URL de PostgreSQL.

---

## 4. Estructura del proyecto

```
frontend/
  index.html
  package.json
  vite.config.ts          Alias "@", proxy /api, configuración de Vitest
  tsconfig.json
  vercel.json             Rewrites a la API, SPA y cabeceras de seguridad
  .env.example
  src/
    main.tsx              Punto de entrada
    app/
      App.tsx             Proveedores + enrutador
      router.tsx          Mapa de rutas públicas y privadas
      providers/          AppProviders (Query, Motion) y AuthProvider (sesión)
    components/
      ui/                 Sistema de diseño: Button, Card, Badge, Input, Select,
                          Modal, Ayuda (tooltip), Avatar, Skeleton, EstadoVacio,
                          PasoConfirmacion
      layout/             AppLayout (barra lateral / inferior), RutaProtegida
      monsters/           Personajes SVG (por ahora: Bienvi)
    features/             Un módulo por funcionalidad (ver sección 5)
      <modulo>/
        <Modulo>Page.tsx  Pantalla: solo compone
        api.ts            Llamadas HTTP y hooks de TanStack Query
        schemas.ts        Validación Zod y conversión al cuerpo de la API
        types.ts          Tipos del contrato del backend
        components/       Piezas de esa pantalla
    hooks/                Hooks compartidos (useClaveIdempotencia)
    lib/                  Utilidades puras: formatCOP, pesos, fechas, errores, cn, navegacion
    services/
      api/client.ts       Cliente HTTP único
      auth/authApi.ts     login, logout, me
    styles/               theme.css (tokens) y globals.css
    types/                Tipos compartidos (sesión, finanzas, paginación)
```

**Regla para evitar código espagueti:** las pantallas solo componen; el HTTP vive en `api.ts`; la validación en `schemas.ts`; los textos y tipos del contrato en `types.ts`. Cada archivo empieza con un comentario con su ruta y cada bloque lleva un comentario de lo que hace.

---

## 5. Módulos y endpoints que consumen

| Ruta del frontend | Módulo | Endpoints del backend | Permiso para modificar |
|---|---|---|---|
| `/` | auth | — | — |
| `/ingresar` | auth | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` | — |
| `/panel` | dashboard | `GET /dashboard/summary` | — |
| `/cuentas` | accounts | `GET/POST /accounts` | `gestionar_cuentas` |
| `/movimientos` | transactions | `GET/POST /transactions`, `POST /transactions/{id}/reverse` | `registrar_movimientos`, `revertir_movimientos` |
| `/aportes` | contributions | `GET /contributions/summary`, `GET /contribution-rules`, `POST /contributions`, `POST /contributions/reimbursements` | `registrar_movimientos` |
| `/obligaciones` | obligations | `GET/POST /obligations`, `POST /obligations/{id}/payments`, `POST /obligations/{id}/cancel` | `gestionar_obligaciones`, `registrar_pagos` |
| `/prestamos` | loans | `GET/POST /loans`, `GET /loans/{id}`, `POST /loans/{id}/payments` | `gestionar_prestamos`, `registrar_pagos` |
| `/informes` | reports | `GET /reports/monthly` (JSON y CSV), `GET /dashboard/summary` | `exportar_informes` (CSV) |
| `/integrantes` | members | `GET/POST /members`, `POST /members/{id}/acceso` | `gestionar_integrantes` |
| `/configuracion` | settings + categories | `GET/POST/PATCH /categories` | `gestionar_categorias` |

Roles del backend: **admin** (todos los permisos) y **miembro** (solo `ver_finanzas`).

Funciones que **no** existen en el backend y por eso no están en la interfaz: buscador y ordenamiento de movimientos, filtro por categoría, resumen anual, edición o desactivación de integrantes, anulación de préstamos, cambio de contraseña, notificaciones y logros.

---

## 6. Sesión, cookies y seguridad

### Sesión
- El backend entrega el token en una cookie **HttpOnly** (`fm_acceso`). JavaScript nunca lo ve ni lo guarda: no hay `localStorage` ni `sessionStorage` con credenciales.
- `AuthProvider` pregunta a `GET /auth/me` al abrir la app. Un `401` en cualquier petición (salvo el login) cierra la sesión local y `RutaProtegida` redirige al ingreso.
- `useAuth().puede(permiso)` solo **oculta** botones. Si alguien fuerza una acción, el backend responde `403`.

### Por qué la API se llama con ruta relativa
El frontend y el backend viven en subdominios distintos de `.vercel.app`, que el navegador considera **sitios distintos**. Con `SameSite=lax` la cookie no viajaría. Por eso `vercel.json` reenvía `/api/*` al backend: el navegador ve un solo origen y no hace falta CORS ni `SameSite=none`.

### Cabeceras (en `vercel.json`)
`Content-Security-Policy` (solo recursos propios, sin scripts externos), `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`.

### Idempotencia (evita registros dobles)
Las operaciones que mueven dinero (movimientos, aportes, reembolsos, pagos, préstamos) envían `Idempotency-Key`:
- Una clave **por intento**, generada con `crypto.randomUUID()` (cumple `^[A-Za-z0-9_-]{8,80}$`).
- Si falla la red o el servidor (0 o 5xx), el reintento usa **la misma clave** (el envío pudo aplicarse).
- Si el backend rechaza la solicitud (4xx), la clave se **renueva**.
- Los botones se bloquean mientras se envía.

### Otras prácticas
- Confirmación en dos pasos (`PasoConfirmacion`) antes de registrar dinero; motivo obligatorio al revertir o anular.
- Validación con Zod en cada formulario (el backend vuelve a validar todo).
- Sin `dangerouslySetInnerHTML`. Los mensajes de error del backend se muestran como texto; el cliente nunca muestra detalles técnicos.
- Los importes llegan como **texto** de pesos enteros (`"1250000"`) y solo se formatean con `formatCOP()`.

---

## 7. Diseño

Identidad: **morado y blanco**, con verde, rojo y amarillo reservados para estados financieros.

| Token | Valor |
|---|---|
| `morado-profundo` | `#24113F` |
| `morado` | `#35165D` |
| `morado-secundario` | `#59318B` |
| `violeta` | `#7042C8` |
| `lavanda` | `#A78BFA` |
| `fondo` | `#F5F3FA` |
| `texto` / `texto-suave` | `#252033` / `#777184` |
| `exito` / `alerta` / `aviso` | `#22C55E` / `#EF4444` / `#F59E0B` |

Para cambiar la paleta se edita **solo** `src/styles/theme.css`.

Responsive: móvil primero. En móvil, barra inferior con 4 secciones y botón **Más**; en tablet, barra lateral de íconos; en escritorio, barra lateral con texto. Objetivos táctiles de 44 px, foco visible y `prefers-reduced-motion` respetado.

---

## 8. Cómo agregar un módulo nuevo

1. Crear `src/features/<modulo>/` con `types.ts`, `schemas.ts`, `api.ts`, `components/` y `<Modulo>Page.tsx`.
2. Tipar según el `schemas.py` real del backend; no inventar campos ni endpoints.
3. Las operaciones con dinero usan `useClaveIdempotencia()` y `PasoConfirmacion`.
4. Registrar la ruta en `src/app/router.tsx` y el enlace en `src/lib/navegacion.ts`.
5. Agregar pruebas y ejecutar `npm run build` y `npm test`.

---

## 9. Pruebas

`npm test` ejecuta 45 pruebas que cubren: formato COP, lectura de importes, cliente HTTP (cookie, idempotencia, errores, sesión vencida), clave de idempotencia, reglas de movimientos y préstamos, protección de rutas, login y el registro de movimientos con confirmación.

Sin pruebas todavía: Cuentas, Obligaciones, Aportes, Informes, Integrantes, Configuración y la navegación móvil.

Nota para escribir pruebas: **no** usar `beforeEach(() => mock.mockReset())` sin llaves; Vitest trata lo que devuelve como función de limpieza. Usar `beforeEach(() => { mock.mockReset(); })`.

---

## 10. Despliegue en Vercel + Neon

### Backend (proyecto Vercel 1)
1. Importar el repositorio y poner **Root Directory** = `backend`. Vercel detecta `index.py` y la variable `app`.
2. Variables de entorno:

| Variable | Valor |
|---|---|
| `ENTORNO` | `produccion` |
| `DATABASE_URL` | Cadena de Neon (con `-pooler`) |
| `DATABASE_URL_MIGRACIONES` | Cadena **directa** de Neon (sin pooler), para Alembic |
| `SECRET_KEY` | Texto aleatorio de 32 o más caracteres (no el de ejemplo) |
| `CORS_ORIGENES` | URL `https://` exacta del frontend, sin barra final |
| `COOKIE_SECURE` | `true` |
| `COOKIE_SAMESITE` | `lax` |
| `SETUP_TOKEN` | Opcional: solo para crear el primer hogar; borrarlo después |

3. Aplicar migraciones con la URL directa: `alembic upgrade head` (desde `backend/`).
4. Comprobar `https://TU-BACKEND.vercel.app/api/v1/preparacion` → debe responder `{"estado":"ok","base_de_datos":"ok"}`.

### Frontend (proyecto Vercel 2)
1. Importar el mismo repositorio con **Root Directory** = `frontend`.
2. Framework: Vite. Build: `npm run build`. Salida: `dist`.
3. Variable: `VITE_API_URL=/api/v1`.
4. En `vercel.json`, reemplazar `https://TU-BACKEND.vercel.app` por la URL real del backend.
5. Desplegar, copiar la URL `.vercel.app` del frontend y ponerla en `CORS_ORIGENES` del backend (si cambió, **redesplegar** el backend).

### Primer hogar
Con `ENTORNO=produccion` la documentación `/api/docs` está oculta. Para crear el primer hogar y administrador, activar temporalmente `DOCS_HABILITADAS=true` y `SETUP_TOKEN`, abrir la documentación **directamente en la URL del backend** (no a través del frontend: su CSP bloquea los scripts de la documentación), crear el hogar y volver a apagar ambas variables.

### Lista de verificación final
- [ ] `npm run build` y `npm test` pasan.
- [ ] `/api/v1/preparacion` responde `ok`.
- [ ] El login funciona y la cookie `fm_acceso` aparece como HttpOnly y Secure.
- [ ] Un usuario *miembro* no ve botones de gestión y el backend le responde `403` si fuerza una acción.
- [ ] `backend/.env.neon` **no** está en GitHub (si lo estuvo, rotar la contraseña de Neon).

---

## 11. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Login correcto pero vuelve al ingreso | La cookie no se guarda | Revisar que `vercel.json` apunte a la URL real del backend y que `COOKIE_SECURE`/`SAMESITE` coincidan con el entorno |
| `403 Origen no autorizado` al registrar | `CORS_ORIGENES` no coincide con el dominio del frontend | Poner la URL exacta `https://…` y redesplegar el backend |
| Error `is not a module` o `any` implícito al compilar | Archivo desactualizado o vacío en tu copia | Reemplazar por la versión entregada y ejecutar `npm run build` |
| La CSP bloquea algo | Se agregó un recurso externo | Los recursos externos no están permitidos; incluirlos en el proyecto o ajustar la CSP con criterio |
| Pantalla en blanco al recargar una ruta | Falta el rewrite SPA | Confirmar la regla `/((?!api/).*)` en `vercel.json` |

---

## 12. Pendientes conocidos

- **Logros, metas y gamificación:** requieren reglas y endpoints en el backend; no se inventan datos.
- **Personajes:** existe Bienvi; faltan Ahorrín, Organi, Analis y Festejo.
- **Reglas de reparto:** solo lectura; falta el formulario de creación.
- **Historial de pagos por obligación:** el endpoint `GET /obligations/{id}` ya lo permite; falta la pantalla.
- **Dependencias:** `npm audit --omit=dev` reporta una advertencia de severidad alta en `zod` (consumo de memoria con colecciones enormes). El riesgo aquí es bajo (solo valida formularios cortos); la actualización a zod 4 es un cambio mayor y debe hacerse con pruebas. **No usar** `npm audit fix --force`.
- **Rendimiento:** el paquete principal pesa unos 690 kB (≈208 kB comprimido); se puede reducir cargando cada pantalla de forma diferida.
- **Accesibilidad:** falta revisión con lector de pantalla y pruebas en dispositivos reales.