<!-- family_monster/backend/README.md -->
<!-- Guía del backend de Familia Monster: qué es, cómo configurarlo, cómo correrlo y cómo funciona el dinero. -->

# Familia Monster — Backend (API)

API privada para administrar las finanzas de un hogar: cuentas, ingresos, gastos, transferencias,
aportes de cada integrante, obligaciones (facturas), préstamos, informes y auditoría.
Todo en **pesos colombianos (COP)** y en español.

## 1. Estado actual

| Parte | Estado |
|---|---|
| Backend (esta carpeta) | Completo en sus módulos principales (ver sección 12 para lo pendiente) |
| Frontend (React, verde y blanco) | **Aún no construido** |
| Base de datos en la nube (Neon / Supabase) | **Aún no configurada** |
| Despliegue en Vercel | **Aún no realizado** |

Hoy el backend se prueba en tu computador con la documentación interactiva (`/api/docs`).

Verificado: **286 pruebas automáticas** contra PostgreSQL 16 en Linux, más un recorrido completo con un servidor real.
**No verificado todavía:** Windows, Neon/Supabase y Vercel.

---

## 2. Conceptos básicos (si nunca has configurado una base de datos)

- **Base de datos (PostgreSQL):** el "archivador" donde se guardan los datos para siempre: cuentas, movimientos,
  usuarios. La aplicación no guarda nada en sí misma; todo va a la base de datos.
- **Tablas y migraciones (Alembic):** una base nueva está vacía, sin tablas. Una *migración* es una receta que
  crea o modifica las tablas. Se aplican con un comando (`alembic upgrade head`) y quedan numeradas
  (`0001`, `0002`, `0003`). Así la base de tu computador y la de producción tienen siempre la misma estructura.
- **Variables de entorno (`.env`):** configuración que cambia según el lugar donde corre la aplicación
  (tu PC, producción) y **que incluye secretos** (contraseña de la base, clave para firmar sesiones).
  Por eso vive en un archivo `.env` que **nunca se sube a GitHub** (lo bloquea el `.gitignore`).
- **API:** el programa que recibe peticiones ("registra este gasto") y responde. El frontend (las pantallas) y
  la documentación interactiva solo son formas de hacerle esas peticiones.
- **Neon / Supabase:** servicios que te prestan una base PostgreSQL en internet (con plan gratuito). Se usarán
  cuando despliegues. **Para desarrollar no los necesitas**: usas PostgreSQL instalado en tu computador.
- **Vercel:** servicio donde se publicará la aplicación en internet. Tampoco se necesita todavía.

---

## 3. Estructura del proyecto

```
family_monster/
├── .gitignore                    ← qué archivos nunca se suben a GitHub
├── backend/                      ← esta carpeta (la API)
│   ├── README.md
│   ├── index.py                  ← archivo de entrada que busca Vercel
│   ├── .python-version           ← fija Python 3.12 en Vercel
│   ├── requirements.txt          ← librerías de producción (versiones fijas)
│   ├── requirements-dev.txt      ← además, librerías para pruebas
│   ├── .env.example              ← plantilla de configuración (SÍ se sube; el .env real NO)
│   ├── alembic.ini  pytest.ini
│   ├── app/
│   │   ├── main.py               ← punto de entrada de la API
│   │   ├── core/                 ← configuración, seguridad, permisos, errores, dependencias
│   │   ├── db/                   ← conexión y base de los modelos
│   │   ├── shared/               ← dinero (COP), fechas, paginación, idempotencia
│   │   └── modules/              ← un dominio por carpeta
│   │       ├── auth/  households/  members/        identidad, hogar e integrantes
│   │       ├── accounts/  categories/              cuentas y categorías
│   │       ├── transactions/                       libro de movimientos (ledger.py = núcleo contable)
│   │       ├── contributions/                      reglas de reparto, aportes, reembolsos
│   │       ├── obligations/  loans/                facturas y préstamos con cuotas
│   │       ├── reports/                            panel principal e informes (CSV)
│   │       └── audit/                              bitácora de auditoría
│   ├── migrations/versions/      ← 0001, 0002, 0003
│   └── tests/
└── frontend/                     ← (pendiente)
```

Cada módulo sigue el mismo molde: `models.py` (tablas) → `schemas.py` (datos de entrada y salida) →
`repository.py` (consultas) → `service.py` (reglas de negocio) → `router.py` (endpoints).
Los endpoints **no** contienen lógica de negocio.

---

## 4. Requisitos

1. **Python 3.12 o superior** (`python --version`). En Windows, marca *"Add Python to PATH"* al instalarlo.
2. **PostgreSQL 14 o superior** instalado en tu computador (instalador de postgresql.org). Anota la contraseña
   del usuario `postgres` y deja el puerto `5432`.
3. Un editor de código (por ejemplo, VS Code) y Git.

---

## 5. Puesta en marcha local

Todos los comandos se ejecutan **dentro de la carpeta `backend/`**.

### 5.1 Entorno virtual e instalación de librerías

```
python -m venv .venv
```

Actívalo:

```
.venv\Scripts\activate            (Windows)
source .venv/bin/activate         (Mac o Linux)
```

> Si PowerShell bloquea el script, ejecuta una vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

```
pip install -r requirements-dev.txt
```

### 5.2 Crear las dos bases de datos

Necesitas **dos**: una para trabajar y una para las pruebas. La de pruebas **debe terminar en `_prueba`**:
las pruebas la vacían, y por seguridad se niegan a correr contra cualquier otra.

Con pgAdmin (clic derecho en *Databases → Create → Database*) o con la terminal:

```
psql -U postgres -c "CREATE DATABASE familia_monster;"
psql -U postgres -c "CREATE DATABASE familia_monster_prueba;"
```

### 5.3 Configurar el `.env`

Copia `.env.example` como `.env` (en la misma carpeta) y genera dos secretos:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Edita el `.env`:

| Variable | Qué poner |
|---|---|
| `DATABASE_URL` | `postgresql://postgres:TU_CLAVE@localhost:5432/familia_monster` (si tu clave tiene `@` o `#`, escríbelos `%40` y `%23`) |
| `SECRET_KEY` | El primer secreto generado |
| `SETUP_TOKEN` | El segundo secreto generado |
| `COOKIE_SECURE` | `false` (en local no hay HTTPS) |
| `ENTORNO` | `desarrollo` |

### 5.4 Crear las tablas

```
alembic upgrade head
```

Debes ver tres líneas `Running upgrade` (`0001`, `0002`, `0003`).

### 5.5 Arrancar el servidor

```
uvicorn app.main:app --reload
```

Abre **http://127.0.0.1:8000/api/docs** (usa exactamente esa dirección o `localhost:8000`).

---

## 6. Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `ENTORNO` | no | `desarrollo`, `pruebas` o `produccion`. En producción se exigen controles de seguridad extra y se oculta la documentación. |
| `DATABASE_URL` | **sí** | Conexión a PostgreSQL. En Neon/Supabase, la URL con *pooler*. |
| `DATABASE_URL_MIGRACIONES` | no | Conexión directa (sin pooler) usada solo por Alembic. |
| `SECRET_KEY` | **sí** | Firma las sesiones. Mínimo 32 caracteres. Nunca compartirla. |
| `DOCS_HABILITADAS` | no | `false` por defecto. En producción, `true` muestra `/api/docs` **solo temporalmente** (para crear el primer hogar). |
| `SETUP_TOKEN` | no | Permite crear el primer hogar. **Bórralo después de usarlo.** |
| `MINUTOS_EXPIRACION_ACCESO` | no | Duración de la sesión (15 por defecto). |
| `CORS_ORIGENES` | no | Direcciones del frontend autorizadas, separadas por coma. En producción solo `https://`. |
| `COOKIE_SECURE` | no | `true` en producción (HTTPS); `false` en local. |
| `COOKIE_SAMESITE` | no | `lax` (recomendado). |
| `USAR_NULLPOOL` | no | `true` en Vercel (serverless). |

---

## 7. Primer uso (todo desde `/api/docs`)

1. **`POST /instalacion`** — crea el hogar y tu administrador. Pega tu `SETUP_TOKEN` en el campo `X-Setup-Token`.
   La contraseña necesita 12 caracteres o más, con letras y números. Funciona **una sola vez**; luego borra
   `SETUP_TOKEN` del `.env`. El hogar nace con 11 categorías (Agua, Energía, Gas, Internet, Mercado, Arriendo,
   Reparaciones, Transporte, Salud, Préstamos, Otros).
2. **`POST /auth/login`** — inicia sesión; el navegador guarda la cookie y el resto de rutas funcionan.
3. **`POST /members`** — registra a cada integrante (con o sin acceso a la app). Para darle acceso:
   **`POST /members/{id}/acceso`**.
4. **`POST /accounts`** — crea las cuentas: efectivo, banco, o `personal` (dinero de un integrante, con `propietario_id`).
5. **`POST /contribution-rules`** — define cómo se reparten los gastos (ver sección 8).
6. **`POST /transactions`**, **`/obligations`**, **`/contributions`**, **`/loans`** — registra el día a día.
7. **`GET /dashboard/summary`** — el panel; **`GET /reports/monthly?mes=2026-10`** — el informe del mes.

> **Importes:** siempre sin puntos ni centavos (`120000`, no `120.000`).
> **`Idempotency-Key`:** las operaciones que mueven dinero la exigen. Escribe un texto único de 8 a 80
> caracteres (por ejemplo `gasto-mercado-0001`) y **usa uno nuevo en cada operación nueva**. Si reenvías la misma
> clave con los mismos datos (por ejemplo, por un fallo de internet), no se duplica.

---

## 8. Cómo funciona el dinero (reglas de negocio)

- **Precisión:** todo se calcula con `Decimal` y se guarda como `NUMERIC`. Nunca `float`. En COP no hay centavos.
- **El saldo no se guarda: se calcula** = saldo inicial + movimientos confirmados. No puede contradecirse con el historial.
- **Nunca saldo negativo:** ninguna operación, ni siquiera una reversión, puede dejar una cuenta bajo cero.
  Saldo a favor (positivo) sí.
- **Cada concepto tiene su tipo** y se cuenta una sola vez: `ingreso`, `gasto`, `transferencia`, `aporte`,
  `reembolso`, `pago_obligacion`, `desembolso_prestamo`, `pago_cuota`, `reversion`.
  Una transferencia no es ingreso ni gasto; un aporte no es un ingreso; una cuota no es un gasto.
- **Nada se borra:** los movimientos confirmados no se editan ni se eliminan (lo garantiza la base de datos con
  *triggers*). Se corrigen con una **reversión** que exige motivo, deja constancia de quién la hizo y conserva el original.
- **Reparto de gastos** (por regla, con vigencia):
  - Un integrante puede tener un **importe fijo**; el resto del gasto se reparte entre los demás por
    **porcentaje** (deben sumar 100) o en **partes iguales**. Las partes siempre suman exactamente el gasto
    (método del mayor resto). Si los fijos superan el gasto, se escalan proporcionalmente.
  - Una regla por categoría prevalece sobre la regla general.
  - Cada gasto guarda una **foto** de cómo se repartió. Cambiar una regla solo rige hacia adelante.
- **Pagos directos:** un gasto o pago de factura hecho desde la **cuenta personal** de un integrante cuenta como
  que pagó por el hogar. El hogar le queda debiendo ese dinero hasta que se registre un **reembolso**
  (del fondo común a su cuenta personal; no puede superar lo que se le debe).
  *Si no quieres que un gasto cuente así, no lo registres desde una cuenta personal.*
- **Aportes esperados vs reales:** `saldo = (aportes + pagos directos − reembolsos) − lo que le correspondía pagar`.
  Positivo = saldo a favor; negativo = pendiente.
- **Obligaciones:** estado calculado (`pendiente`, `parcialmente_pagada`, `pagada`, `vencida`, `anulada`) a partir de
  pagos confirmados. Ejemplo: factura de $250.000 con un pago de $100.000 → saldo pendiente $150.000.
- **Préstamos:** al crearlos se registra el desembolso y las cuotas (iguales, que suman exactamente el total a pagar;
  si hay intereses, se indican en `total_a_pagar`). Tres tipos: `entre_integrantes` (cuentas personales),
  `al_hogar` (el hogar recibe) y `del_hogar` (el hogar presta). No se revierte un desembolso con cuotas pagadas.
- **Aislamiento:** cada consulta se limita al hogar del usuario autenticado. El hogar nunca se toma de lo que envía el cliente.
- **Fechas:** en zona horaria de Colombia. No se aceptan movimientos con fecha futura.

---

## 9. Endpoints (prefijo `/api/v1`)

**Ver** = cualquier integrante con acceso. **Admin** = solo administradores.

| Método | Ruta | Quién | Para qué |
|---|---|---|---|
| GET | `/salud` | público | Estado del servicio |
| POST | `/instalacion` | token | Crear el primer hogar (una sola vez) |
| POST | `/auth/login` · `/auth/logout` | público / sesión | Iniciar y cerrar sesión |
| GET | `/auth/me` | Ver | Quién soy, mi hogar, mi rol |
| GET | `/households/current` | Ver | Datos del hogar |
| GET · POST | `/members` | Ver · Admin | Listar / crear integrantes |
| POST | `/members/{id}/acceso` | Admin | Dar acceso a la app |
| GET · POST | `/accounts` | Ver · Admin | Cuentas con su saldo / crear |
| GET · POST · PATCH | `/categories` | Ver · Admin | Categorías |
| GET · POST | `/transactions` | Ver · Admin | Movimientos (ingreso, gasto, transferencia) |
| POST | `/transactions/{id}/reverse` | Admin | Revertir un movimiento |
| GET · POST | `/contribution-rules` | Ver · Admin | Reglas de reparto |
| GET | `/contributions/summary` | Ver | Aportes esperados y reales |
| GET | `/contributions/distributions/{id}` | Ver | Cómo se repartió un gasto |
| POST | `/contributions` · `/contributions/reimbursements` | Admin | Aportes y reembolsos |
| GET · POST | `/obligations` · `/obligations/{id}` | Ver · Admin | Obligaciones |
| POST | `/obligations/{id}/payments` · `/cancel` | Admin | Pagar / anular |
| GET · POST | `/loans` · `/loans/{id}` | Ver · Admin | Préstamos y cuotas |
| POST | `/loans/{id}/payments` | Admin | Pagar una cuota |
| GET | `/dashboard/summary` | Ver | Panel principal |
| GET | `/reports/monthly?mes=AAAA-MM` | Ver | Informe mensual (JSON) |
| GET | `/reports/monthly?mes=AAAA-MM&formato=csv` | Admin | Exportar a CSV |
| GET | `/audit` | Admin | Bitácora de auditoría |

Los listados aceptan `?limite=` (1 a 100) y `?desplazamiento=`. Los errores siempre tienen el formato
`{"error": {"codigo", "mensaje", "detalle"}}`, en español.

---

## 10. Pruebas

Con el entorno virtual activado, desde `backend/`, indica la base de **pruebas** y ejecuta:

```
set TEST_DATABASE_URL=postgresql://postgres:TU_CLAVE@localhost:5432/familia_monster_prueba       (Windows cmd)
$env:TEST_DATABASE_URL="postgresql://postgres:TU_CLAVE@localhost:5432/familia_monster_prueba"    (PowerShell)
export TEST_DATABASE_URL=postgresql://postgres:TU_CLAVE@localhost:5432/familia_monster_prueba    (Mac o Linux)

python -m pytest
```

Debes ver `286 passed`. Si ves muchos `skipped`, PostgreSQL no está disponible: **no cuentan como aprobadas**.

- Las pruebas **vacían** la base `_prueba` y recrean las tablas con las migraciones reales (también prueban
  que se puedan revertir). Nunca las apuntes a tu base de trabajo.
- Una advertencia de Pydantic sobre `alias` puede aparecer en las pruebas de concurrencia (varios hilos a la
  vez); viene de las librerías, no afecta los resultados.

Qué cubren: precisión y reparto del dinero, permisos por rol, aislamiento entre hogares, idempotencia,
concurrencia real (varias solicitudes simultáneas), reversiones, estados derivados, informes que coinciden con el
libro, y las barreras de la propia base de datos.

---

## 11. Seguridad

Controles implementados y probados:

- Contraseñas con **Argon2id**; política de 12+ caracteres con letras y números.
- Sesión en cookie **HttpOnly** (JavaScript no puede leerla), firmada, de 15 minutos; rechaza tokens falsos, vencidos o `alg=none`.
- **Bloqueo por intentos de login:** 5 fallos bloquean el correo 15 minutos (también con correos inexistentes, sin revelar cuáles existen).
- Permisos validados **en el backend** en cada petición; el hogar sale de la base de datos, nunca del cliente.
- **CSRF:** las escrituras desde un origen no autorizado se rechazan.
- **CORS** restringido; cabeceras de seguridad; documentación desactivada en producción.
- **Idempotencia** y candados para evitar duplicados y carreras (pagos simultáneos, saldos, reembolsos).
- **Auditoría** de acciones sensibles (incluida la exportación a CSV); el CSV neutraliza fórmulas de Excel.
- Historial **inmutable** a nivel de base de datos.
- Secretos solo en variables de entorno; el `.gitignore` bloquea `.env`.

---

## 12. Pendiente y limitaciones conocidas

Lo que **aún no existe**:

- **Comprobantes (archivos adjuntos)**: subir facturas o recibos con almacenamiento privado. Es el módulo 8 del diseño y falta.
- **Cambio y recuperación de contraseña.** Hoy el administrador fija la contraseña inicial.
- **Desactivar** cuentas e integrantes (la base ya lo soporta; falta el endpoint).
- **Exportación a Excel o PDF** (solo existe CSV).
- Frontend, despliegue y copias de seguridad (próximas fases).

Limitaciones a tener presentes:

- La sesión es *stateless* (15 minutos): al cerrar sesión se borra la cookie, pero un token ya emitido sigue
  siendo válido hasta vencer. Desactivar a un usuario sí corta su acceso de inmediato.
- El bloqueo por intentos protege el **login**. No hay aún un límite general de peticiones por IP; en
  producción se recomienda agregarlo en el borde (Vercel).
- Los intentos de login fallidos de correos inexistentes se acumulan en una tabla y necesitarán una limpieza periódica.
- Con dos dominios `*.vercel.app` distintos para frontend y backend, la cookie de sesión no se enviaría. Se
  recomienda un dominio propio con subdominios (`app.` y `api.`). **Decisión pendiente antes de desplegar.**
- Los reglas de reparto no se editan: se crea una nueva con una fecha posterior (así se protege el historial).
- Un informe mensual incluye hasta 5.000 movimientos (el resultado indica si quedó truncado).

---

## 13. Despliegue

Plan: base PostgreSQL en **Neon**, backend (y más adelante el frontend) en **Vercel**, código en **GitHub**, todo
con direcciones gratuitas `*.vercel.app` (sin dominio propio).

**Guía completa paso a paso: [`../docs/INSTRUCTIVO_CONFIGURACION.md`](../docs/INSTRUCTIVO_CONFIGURACION.md)**
(incluye la arquitectura de cookies sin dominio propio, migraciones sobre Neon, variables de Vercel, copias de
seguridad, lista de seguridad y solución de problemas).

**No hace falta nada de eso para trabajar en local.**

---

## 14. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `ValidationError ... database_url` al arrancar | Falta el `.env`, no está dentro de `backend/`, o ejecutas desde otra carpeta. |
| `ModuleNotFoundError: app` | Estás fuera de `backend/`, o falta algún `__init__.py`. |
| `password authentication failed` | Clave incorrecta en `DATABASE_URL`, o caracteres especiales sin codificar (`@` → `%40`). |
| `relation "..." does not exist` | Faltó `alembic upgrade head`. |
| `alembic` no encuentra la carpeta de versiones | Crea `migrations/versions/`. |
| 403 "Origen no autorizado" desde `/api/docs` | Abre la dirección exacta del servidor (`127.0.0.1:8000`) y no otra. |
| 429 al iniciar sesión | 5 intentos fallidos bloquean el correo durante 15 minutos. |
| 422 "Saldo insuficiente" | La cuenta no tiene fondos; el sistema nunca permite saldo negativo. |
| 409 con la `Idempotency-Key` | Reutilizaste una clave con datos distintos; usa una nueva. |
| Las pruebas se niegan a correr | El nombre de la base de pruebas no termina en `_prueba`. |
| Las pruebas aparecen como `skipped` | PostgreSQL no está accesible con `TEST_DATABASE_URL`. |