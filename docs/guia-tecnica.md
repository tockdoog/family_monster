<!-- docs/guia-tecnica.md -->
<!-- Guía técnica de Familia Monster: base de datos, consultas SQL, lógica del sistema y qué hacer al ajustar backend o frontend. -->
<!-- No contiene secretos: las URL reales viven solo en backend/.env.neon, que Git ignora. -->

# Guía técnica de Familia Monster

Última revisión: 31/10/2026.

> **Cómo leer esta guía.** Lo marcado como **Verificado** se comprobó con código o con las 266 pruebas del backend.
> Lo marcado como **Por confirmar** se dedujo de la estructura del proyecto: contrástelo con el archivo indicado antes de apoyarse en ello.

## Índice

1. Mapa del sistema
2. Reglas de oro
3. Entorno de desarrollo local
4. La base de datos
5. Consultas SQL
6. Lógica del sistema
7. Ajustar el backend
8. Ajustar el frontend
9. Si cambio X, ¿qué hago?
10. Comprobación después de publicar
11. Problemas frecuentes
12. Pendientes y mejoras recomendadas
13. Documentos relacionados

---

## 1. Mapa del sistema

```
Navegador
   |  https://familia-monster.vercel.app
   v
Vercel: proyecto "familia-monster" (carpeta frontend, React + TypeScript + Vite)
   |  vercel.json reenvía /api/*  (rewrite, mismo origen para el navegador)
   v
Vercel: proyecto "familia-monster-api" (carpeta backend, FastAPI)
   |  consultas SQL con la URL CON pooler (DATABASE_URL)
   v
Neon: proyecto "familia-monster", rama "production", base "neondb" (PostgreSQL)

Su computador --> Neon, con la URL DIRECTA (DATABASE_URL_MIGRACIONES): migraciones y copias
GitHub (rama main) --> Vercel: cada push publica los proyectos de este repositorio
```

| Pieza | Dónde vive | Carpeta del repositorio |
|---|---|---|
| Frontend | Vercel, proyecto `familia-monster` | `frontend/` |
| API | Vercel, proyecto `familia-monster-api` | `backend/` |
| Base de datos | Neon (plan gratuito) | `backend/migrations/` define su esquema |

Por qué hay dos proyectos en Vercel: cada uno compila una tecnología distinta (Node/Vite y Python) y mira una sola carpeta (su *Root Directory*). Los dos salen del mismo repositorio.

---

## 2. Reglas de oro

1. Nunca pegue en un chat, en GitHub ni en capturas: contraseñas, URL con contraseña, `SECRET_KEY`, `SETUP_TOKEN` ni el contenido de `.env.neon`.
2. Las credenciales de Neon viven solo en `backend/.env.neon` (Git lo ignora con la regla `.env.*`) y, como variables Sensitive, en Vercel.
3. `backend/.env` es solo para desarrollo local y apunta a una base **local**. Nunca ponga ahí datos de Neon.
4. Con `.env.neon` cargado, nunca ejecute `pytest` ni `alembic downgrade`: ambos borran tablas.
5. En producción, el SQL manual es de **solo lectura** (`SELECT`). Los datos se cambian desde la aplicación.
6. Antes de cualquier migración contra Neon: copia de seguridad (`docs/recuperacion.md`).
7. Antes de `git push`: `pytest` (backend) y `npm run build` y `npm test` (frontend) en verde, y `git status` sin `.env`, `.dump`, `node_modules/` ni `backups/`.
8. Si algo falla, no pegue logs con URL de base de datos: diga solo el mensaje del error.

---

## 3. Entorno de desarrollo local

Hay **tres** bases de datos distintas. No las mezcle:

| Base | Dónde | Para qué | Se puede borrar |
|---|---|---|---|
| `familia_monster_prueba` | PostgreSQL local | Pruebas automáticas (`pytest`) | Sí, `pytest` la vacía solo |
| `familia_monster_dev` | PostgreSQL local | Probar la app a mano con datos inventados | Sí |
| `neondb` | Neon | Producción, datos reales | **No** |

### 3.1 Crear la base de desarrollo (una sola vez)

Con `pg_dump` y compañía en el PATH de la terminal (`export PATH="$PATH:/c/Program Files/PostgreSQL/18/bin"`):

```
createdb -U postgres -h localhost familia_monster_dev
```

Cree `backend/.env` (solo desarrollo local, Git lo ignora):

```
# backend/.env
ENTORNO=desarrollo
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/familia_monster_dev
SECRET_KEY=un-secreto-local-de-al-menos-32-caracteres-123456
COOKIE_SECURE=false
CORS_ORIGENES=http://localhost:5173
USAR_NULLPOOL=true
SETUP_TOKEN=un-token-local-de-al-menos-24-caracteres-1
```

Cree las tablas en esa base (desde `backend/`, con el entorno virtual activo):

```
alembic upgrade head
```

### 3.2 Arrancar la API local

`uvicorn` no está en `requirements.txt` (Vercel no lo necesita). Solo local:

```
pip install uvicorn
uvicorn app.main:app --reload --port 8000
```

- La documentación interactiva queda en `http://localhost:8000/api/docs` (en producción está oculta a propósito). Ahí se ven **todos** los endpoints y sus esquemas.
- Para crear un hogar de prueba: en `/api/docs`, `POST /api/v1/instalacion`, con la cabecera `X-Setup-Token` igual a `SETUP_TOKEN` de su `.env`.

### 3.3 Arrancar el frontend local

```
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. El proxy de `vite.config.ts` reenvía `/api` a `http://localhost:8000`, así que la cookie de sesión funciona sin CORS. **Siempre** contra su base de desarrollo, nunca contra Neon.

---

## 4. La base de datos

### 4.1 Dónde vive

- Producción: Neon, proyecto `familia-monster`, rama `production`, base `neondb`, rol `neondb_owner`, región AWS US East 1.
- Ventana de restauración de Neon gratuito: solo 6 horas. Por eso existen las copias propias.
- Las condiciones de los planes gratuitos cambian: confirme siempre en el panel de Neon.

### 4.2 Tablas por área (**Verificado**: lista de `conftest.py` y de Neon)

| Área | Tablas |
|---|---|
| Identidad | `users`, `households`, `memberships`, `members`, `login_attempts` |
| Dinero | `accounts`, `categories`, `transactions`, `transaction_lines` |
| Aportes | `contribution_rules`, `contribution_rule_items`, `contribution_shares` |
| Obligaciones | `obligations`, `obligation_payments` |
| Préstamos | `loans`, `installments`, `installment_payments` |
| Auditoría | `audit_logs` |
| Control de migraciones | `alembic_version` |

### 4.3 Relaciones principales

```
households 1---* memberships *---1 users      (quién entra a qué hogar y con qué rol)
households 1---* members                       (integrantes; pueden o no tener usuario)
households 1---* accounts, categories

transactions 1---* transaction_lines *---1 accounts
   (cada movimiento tiene líneas con importe con signo: negativo sale de una cuenta, positivo entra)

obligations 1---* obligation_payments *---1 transactions
loans 1---* installments 1---* installment_payments *---1 transactions
transactions 1---* contribution_shares        (reparto del gasto entre integrantes)
```

Casi todas las tablas llevan `household_id`. Las claves foráneas compuestas `(id, household_id)` impiden a nivel de base de datos que un registro apunte a otro hogar.

### 4.4 Reglas que protege la propia base (**Verificado** con `test_integridad_modulos_bd.py`)

- `contribution_shares`, `contribution_rule_items`, `obligation_payments` e `installment_payments` no se pueden borrar ni modificar, ni siquiera con SQL directo.
- Importes de obligaciones deben ser positivos; el vencimiento no puede ser anterior a la creación; una obligación anulada exige motivo y responsable.
- Un préstamo no puede tener un total menor a lo prestado ni cero cuotas; el tipo debe ser coherente con sus partes.
- No hay dos reglas de aporte del mismo alcance que empiecen el mismo día.
- Un movimiento no puede pagar dos obligaciones.
- Transferencias y reembolsos deben sumar cero (triggers `verificar_transferencia_balanceada` y afines). Un reembolso descuadrado no se puede confirmar.
- Solo existen los tipos de movimiento definidos; un tipo inventado es rechazado.
- Una categoría usada por una obligación no se puede borrar.
- El historial financiero está protegido por el trigger `proteger_historial_financiero`.

Consecuencia práctica: los errores no se "editan", se **corrigen con un movimiento nuevo** (reversión).

### 4.5 Dinero e identificadores

- Moneda: pesos colombianos (COP). Zona horaria del hogar: `America/Bogota`.
- En el backend los importes son `Decimal` (nunca `float`). En el frontend se muestran con `formatCOP` (`src/lib/formatCOP.ts`), sin decimales y con separadores de `es-CO`: `$ 100.000`.
- Los identificadores son UUID.

### 4.6 Comprobar la versión del esquema

```sql
SELECT * FROM alembic_version;
```

Debe devolver la última migración (hoy `0003`). Si Neon y el código tienen versiones distintas, la API puede fallar.

---

## 5. Consultas SQL

### 5.1 Dónde ejecutarlas

| Opción | Cuándo | Credenciales |
|---|---|---|
| **SQL Editor de Neon** (panel de Neon, Postgres database, SQL Editor) | Mirar datos de producción | Ninguna: ya está dentro de su cuenta |
| **pgAdmin / `psql` contra la base local** | Practicar y probar | La contraseña local de `postgres` |
| `psql` contra Neon desde su computador | Casos especiales | URL directa; no la imprima ni la pegue |

Para producción, recomendado: el **SQL Editor de Neon**, solo con `SELECT`.

### 5.2 Reglas para SQL en producción

1. Solo `SELECT`. No ejecute `UPDATE`, `DELETE`, `TRUNCATE`, `DROP` ni `ALTER` en `neondb`.
2. Ese editor trabaja como `neondb_owner`, con todos los permisos. Revise cada consulta antes de ejecutarla.
3. No consulte `users.password_hash` ni lo copie a ningún lado.
4. Los resultados son datos financieros reales: no los comparta en capturas.
5. Si alguna vez debe escribir datos: copia de seguridad primero, y pruebe antes en la base local.

### 5.3 Explorar la base

Lista de tablas:

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
```

Columnas de una tabla (cambie el nombre; sirve para confirmar cualquier columna antes de escribir una consulta):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'accounts'
ORDER BY ordinal_position;
```

Filas aproximadas por tabla:

```sql
SELECT relname AS tabla, n_live_tup AS filas FROM pg_stat_user_tables ORDER BY relname;
```

Tamaño de la base (compárelo con el límite del plan en el panel de Neon):

```sql
SELECT pg_size_pretty(pg_database_size(current_database())) AS tamano;
```

### 5.4 Consultas de referencia

Las columnas usadas aquí salen del código del backend. Si alguna da error de columna inexistente, confírmela con la consulta de columnas de la sección 5.3.

Quién tiene acceso a qué hogar (sin contraseñas):

```sql
SELECT h.nombre AS hogar, m.rol, u.email, u.nombre_completo
FROM memberships m
JOIN users u ON u.id = m.user_id
JOIN households h ON h.id = m.household_id
ORDER BY h.nombre, m.rol;
```

Cuentas del hogar:

```sql
SELECT nombre, tipo, saldo_inicial FROM accounts ORDER BY nombre;
```

Últimos movimientos con sus líneas:

```sql
SELECT t.fecha, t.tipo, t.estado, t.descripcion, a.nombre AS cuenta, l.importe
FROM transactions t
JOIN transaction_lines l ON l.transaction_id = t.id
JOIN accounts a ON a.id = l.account_id
ORDER BY t.fecha DESC, t.creado_en DESC
LIMIT 20;
```

Movimientos por tipo y estado:

```sql
SELECT tipo, estado, count(*) AS cantidad FROM transactions GROUP BY tipo, estado ORDER BY tipo, estado;
```

Obligaciones y lo pagado (solo cuentan los pagos cuyo movimiento sigue confirmado, igual que en la aplicación):

```sql
SELECT o.descripcion, o.acreedor, o.importe_original, o.fecha_vencimiento,
       COALESCE(SUM(p.importe) FILTER (WHERE t.estado = 'confirmada'), 0) AS pagado
FROM obligations o
LEFT JOIN obligation_payments p ON p.obligation_id = o.id
LEFT JOIN transactions t ON t.id = p.transaction_id
GROUP BY o.id
ORDER BY o.fecha_vencimiento;
```

Préstamos y cuotas con lo pagado:

```sql
SELECT l.contraparte_nombre, l.tipo, l.importe, l.total_a_pagar,
       i.numero, i.fecha_vencimiento, i.importe AS cuota,
       COALESCE(SUM(p.importe) FILTER (WHERE t.estado = 'confirmada'), 0) AS pagado
FROM loans l
JOIN installments i ON i.loan_id = l.id
LEFT JOIN installment_payments p ON p.installment_id = i.id
LEFT JOIN transactions t ON t.id = p.transaction_id
GROUP BY l.id, i.id
ORDER BY l.fecha, i.numero;
```

Control de integridad: transferencias y reembolsos que no suman cero (debe devolver **cero filas**):

```sql
SELECT t.id, t.tipo, SUM(l.importe) AS suma
FROM transactions t
JOIN transaction_lines l ON l.transaction_id = t.id
WHERE t.tipo IN ('transferencia', 'reembolso')
GROUP BY t.id, t.tipo
HAVING SUM(l.importe) <> 0;
```

Auditoría (**Por confirmar** los nombres de columna; mírelos primero con la consulta de columnas y ordene por la columna de fecha que exista):

```sql
SELECT * FROM audit_logs LIMIT 20;
```

### 5.5 Saldo de una cuenta

El saldo **no se guarda**: se calcula a partir de `saldo_inicial` y de las líneas de movimientos. La fórmula oficial, que decide cómo cuentan las reversiones, está en `backend/app/modules/accounts/repository.py` (función `saldos_de`). No invente una fórmula propia en SQL: si necesita el saldo, use la pantalla de Cuentas o replique exactamente esa función y compare con lo que muestra la aplicación.

### 5.6 Cambiar datos: por la aplicación, no por SQL

- Para corregir un movimiento: reversión (`POST /api/v1/transactions/{id}/reverse`, con motivo obligatorio). Queda trazable.
- Para una obligación mal creada: anularla (con motivo). Si tiene pagos, primero se revierten esos pagos.
- Los triggers impiden editar o borrar el historial financiero aunque se intente.

### 5.7 Consultar la API ya autenticado

Útil para ver exactamente lo que recibe el frontend. Pide la contraseña por teclado; cambie el correo y la ruta (por ejemplo `/accounts`, `/households/current`, `/transactions`):

```
read -s -p "Contraseña: " FM_PASS; echo
export FM_PASS
python - <<'PY'
import json, os, urllib.request, urllib.error, http.cookiejar
base = "https://familia-monster-api.vercel.app/api/v1"
ruta = "/households/current"
jar = http.cookiejar.CookieJar()
abrir = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar)).open

def llamar(ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(base + ruta, data=datos, method="POST" if cuerpo is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with abrir(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")

estado, _ = llamar("/auth/login", {"email": "correo@ejemplo.com", "contrasena": os.environ["FM_PASS"]})
print("login:", estado)
estado, cuerpo = llamar(ruta)
print(estado, json.dumps(cuerpo, indent=2, ensure_ascii=False)[:3000])
PY
unset FM_PASS
```

---

## 6. Lógica del sistema

### 6.1 Capas del backend (**Verificado**)

Cada módulo de `backend/app/modules/<modulo>/` repite el mismo diseño:

| Archivo | Responsabilidad |
|---|---|
| `router.py` | Recibe la solicitud, valida permisos y delega. Sin lógica de negocio |
| `schemas.py` | Contratos de entrada y salida (Pydantic) |
| `service.py` | Reglas de negocio y orquestación |
| `repository.py` | Consultas a la base. **Todas filtran por hogar** |
| `models.py` | Tablas y restricciones (SQLAlchemy) |

Otras carpetas:
- `core/`: `config.py` (variables y validaciones de producción), `security.py` (Argon2id, JWT, cookie), `exceptions.py` (errores y su formato), `permissions.py`, `dependencies.py`.
- `db/`: `session.py` (motor, sesiones y transacción por solicitud) y `base.py`.
- `shared/`: `money.py`, `fechas.py`, `idempotency.py`, `pagination.py`.

Regla para no crear código espagueti: una regla de negocio nueva va en `service.py`; una consulta nueva, en `repository.py`; el router solo conecta.

### 6.2 Sesión y seguridad (**Verificado**)

- Contraseñas con Argon2id. Política: 12 a 128 caracteres, con letras y números.
- Al iniciar sesión, la API entrega un JWT de 15 minutos en la cookie `fm_acceso`: `HttpOnly` (JavaScript no la lee), `Secure` (solo HTTPS) y `SameSite=lax`.
- El hogar **no** viaja en el token: se consulta siempre en la base. El identificador del hogar nunca se recibe del cliente.
- Los intentos de acceso se registran en `login_attempts` (funciona en serverless porque vive en la base) y un exceso responde 429.
- Defensa CSRF: toda escritura (POST, PUT, PATCH, DELETE) con cabecera `Origin` debe venir del propio servidor o de `CORS_ORIGENES`. Otra cosa responde 403 `origen_no_permitido`.
- Cabeceras de seguridad en todas las respuestas; en producción también HSTS. La documentación `/api/docs` está oculta salvo que `DOCS_HABILITADAS=true`.
- La instalación inicial solo existe si hay `SETUP_TOKEN`; funciona una sola vez.

### 6.3 Varios hogares, un solo código

Cada consulta filtra por `household_id`. Un recurso de otro hogar responde 404, igual que uno que no existe: no se revela que existe. Los permisos dependen del rol de la membresía (`admin`, `miembro`...); el frontend los usa solo para mostrar u ocultar opciones, y el backend valida cada petición.

### 6.4 Libro contable (**Verificado**)

Todo movimiento de dinero pasa por `transactions/ledger.py` (`registrar_asiento`):
1. Valida que la fecha no sea futura.
2. Verifica que cuentas, integrantes y categoría existan en **este** hogar y estén activos.
3. Bloquea las cuentas involucradas, para que dos operaciones simultáneas no gasten el mismo saldo.
4. Rechaza saldo negativo.
5. Crea la cabecera, las líneas (importe con signo) y la auditoría en una sola transacción.

Tipos de movimiento: `ingreso`, `gasto`, `transferencia`, `reversion`, `aporte`, `reembolso`, `pago_obligacion`, `desembolso_prestamo`, `pago_cuota`. Cada uno es un tipo propio: un pago de cuota no es un gasto ni un ingreso.

### 6.5 Reversiones

Un movimiento no se edita ni se borra. Se contrarresta con una reversión trazable (motivo obligatorio). El original pasa a estado `revertida`, y los pagos asociados a movimientos revertidos dejan de contar como pagados.

### 6.6 Idempotencia (**Verificado**)

Las operaciones que mueven dinero exigen la cabecera `Idempotency-Key` (8 a 80 caracteres: letras, números, `-` y `_`).
- Misma clave y mismos datos: responde **200** con el resultado original y no cobra otra vez.
- Misma clave con datos distintos: **409**.
- Dos solicitudes idénticas simultáneas: un candado de PostgreSQL por (hogar, clave) hace que la segunda espere y encuentre el resultado de la primera.
- El frontend genera la clave con `crypto.randomUUID()` (`useClaveIdempotencia`) y la reutiliza en los reintentos del mismo envío.

Al añadir un endpoint que mueva dinero, debe seguir el mismo patrón: `resolver_idempotencia` primero, y una función en el repositorio que devuelva el resultado original para el reintento. Esa función faltante fue el motivo de los tres errores 500 que se corrigieron.

### 6.7 Estados que se calculan, no se guardan

- Obligación: `pendiente`, `parcialmente_pagada`, `vencida`, `pagada`, `anulada`. Prioridad: anulada, pagada, vencida, parcial, pendiente.
- Cuota: `pendiente`, `parcialmente_pagada`, `vencida`, `pagada`.
- Préstamo: `activo`, `pagado`, `anulado` (anulado si su desembolso fue revertido).
- Saldo de cuentas: derivado de las líneas.

Por eso no pueden contradecirse con el libro.

### 6.8 Aportes y reparto

Las reglas de aporte (`contribution_rules` y sus ítems) definen cómo se reparte un gasto entre integrantes. Al registrar un gasto o pagar una obligación, se guarda una "foto" del reparto (`contribution_shares`), que no se modifica después. El reparto solo cuenta mientras el movimiento siga confirmado.

### 6.9 Auditoría

`audit_logs` registra quién hizo qué: hogar creado, movimiento registrado, obligación creada, pagada o anulada, préstamo creado, cuota pagada, etc. Se escribe dentro de la misma transacción que la operación.

### 6.10 Errores

Todo error de la API tiene el mismo formato, en español:

```json
{"error": {"codigo": "no_encontrado", "mensaje": "El recurso solicitado no existe.", "detalle": null}}
```

El frontend lo lee en `src/services/api/client.ts` (`ErrorApi`). Un 401 fuera de `/auth/login` cierra la sesión local; un error 500 nunca expone detalles internos (el detalle va a los logs del servidor).

### 6.11 Arquitectura del frontend (**Verificado** con la estructura y `client.ts`)

| Capa | Dónde | Qué hace |
|---|---|---|
| Rutas | `src/app/router.tsx`, `RutaProtegida.tsx` | Públicas (`/`, `/ingresar`) y privadas dentro del layout |
| Sesión | `src/app/providers/AuthProvider.tsx` | Pregunta a `/auth/me` al abrir; `puede(permiso)` para mostrar u ocultar opciones |
| Cliente HTTP | `src/services/api/client.ts` | Único punto de salida: cookie con `credentials: "include"`, clave de idempotencia, errores |
| Por función | `src/features/<modulo>/` | `api.ts` (consultas con TanStack Query), `types.ts`, `schemas.ts` (Zod), `components/`, `<Modulo>Page.tsx` |
| Interfaz común | `src/components/ui/` | Botón, tarjeta, modal, campos y demás |
| Utilidades | `src/lib/` | `formatCOP`, `pesos`, `fechas`, `errores`, `cn` |
| Tema | `src/styles/theme.css` | Tokens de diseño (paleta morada). Para cambiar colores, solo este archivo |

El frontend **no** calcula saldos oficiales ni valida reglas financieras: solo presenta lo que responde el backend.

### 6.12 Una operación de principio a fin: pagar una obligación

1. El formulario valida con Zod y genera la `Idempotency-Key`.
2. `client.ts` envía el POST a `/api/v1/...`, con la cookie.
3. Vercel (frontend) reenvía `/api/*` a la API; la API verifica el `Origin`, la sesión y el permiso.
4. El servicio bloquea la obligación, comprueba el saldo pendiente y llama al libro.
5. El libro bloquea la cuenta, valida el saldo y crea el movimiento con sus líneas.
6. Se vincula el pago, se reparte el gasto, se audita y se confirma la transacción.
7. Si algo falla en cualquier punto, todo se revierte. Si todo sale bien, responde 201.
8. Si el usuario reintenta con la misma clave, responde 200 con el resultado original.

---

## 7. Ajustar el backend

### 7.1 Flujo general

1. Trabaje en local, contra `familia_monster_dev` (sección 3). Nunca contra Neon.
2. Haga el cambio en la capa que corresponde (sección 6.1).
3. Añada o ajuste pruebas en `backend/tests/`.
4. Ejecute `pytest` en **una sola terminal** hasta ver todo en verde (hoy: 266 pruebas).
5. Si cambió el esquema: migración (7.2), copia de seguridad y migración de Neon (7.3).
6. Si cambió un contrato de la API: actualice el frontend (sección 8.4).
7. `git status` limpio de secretos; `git add`, `git commit`, `git push` a `main`.
8. Vercel publica `familia-monster-api` solo. Verifique (sección 10).

### 7.2 Cambiar el esquema: migración de Alembic

Desde `backend/`, con el entorno virtual activo y `.env` apuntando a la base de desarrollo:

```
alembic revision --rev-id 0004 -m "descripcion corta"
```

Cambie el número `0004` por el siguiente. Se crea un archivo en `backend/migrations/versions/` con fecha, número y descripción, siguiendo el formato de las existentes.

1. Escriba `upgrade()` y `downgrade()` a mano y revíselos: los triggers y las restricciones no se generan solos.
2. Pruébela en local: `alembic upgrade head`, luego `alembic downgrade -1` y de nuevo `alembic upgrade head`.
3. Actualice `models.py` del módulo para que coincida.
4. Ejecute `pytest`: recrea el esquema bajando a `base` y subiendo a `head`, lo que prueba que la migración sea reversible.
5. Nota: una migración no puede revertirse mientras existan movimientos de los tipos que ella introdujo. Es intencional.

### 7.3 Aplicar la migración en Neon

1. Copia de seguridad (`docs/recuperacion.md`, sección 2).
2. Desde `backend/`, lea la URL directa de `.env.neon` sin imprimirla:

```
python -c "
import os, sys
from dotenv import dotenv_values
os.environ.update({k: v for k, v in dotenv_values('.env.neon').items() if v})
from alembic.config import main
main(argv=sys.argv[1:])
" upgrade head
```

3. Compruebe con el mismo comando terminando en `current`: debe mostrar la nueva versión.
4. **Orden con el despliegue:**
   - Cambios **aditivos** (columna nueva opcional, tabla nueva): migre primero y luego haga `push`.
   - Cambios **destructivos** (borrar o renombrar columnas): hágalos en dos pasos. Primero publique código que ya no use la columna; después elimínela con otra migración.
5. Nunca ejecute `downgrade` contra Neon. Si algo sale mal, restaure la copia.

### 7.4 Variables de entorno nuevas

1. Léala en `backend/app/core/config.py` con su validación.
2. Documéntela en `backend/.env.example` (sin valores reales).
3. En Vercel, proyecto `familia-monster-api`, **Environment Variables** (menú principal del proyecto, no Settings), solo Production; Sensitive si es secreta.
4. Las variables solo aplican a despliegues nuevos: **Redeploy**.

### 7.5 Cambios de contrato de la API

- Si **agrega** campos: despliegue primero el backend, después el frontend.
- Si **quita o renombra** campos: adapte primero el frontend para tolerar ambos, despliegue, y recién entonces cambie el backend.
- Actualice `types.ts`, `schemas.ts` y `api.ts` de la función afectada en el frontend.

### 7.6 Volver atrás

- Código: en Vercel, proyecto afectado, **Deployments**, el despliegue anterior, **Instant Rollback**, o `git revert` y `push`.
- Base de datos: Instant Rollback **no** deshace migraciones ni datos. Para eso, la copia de seguridad.
- Neon permite restaurar hasta 6 horas atrás desde Backup & Restore. Úselo con cuidado: sobrescribe la rama `production`.

---

## 8. Ajustar el frontend

### 8.1 Flujo general

1. Con la API local arrancada (sección 3.2), ejecute `npm run dev` dentro de `frontend/`.
2. Haga el cambio en su capa (sección 6.11).
3. Antes de publicar, en `frontend/`:

```
npm run build
npm test
```

`build` ejecuta `tsc --noEmit` y `vite build`: si TypeScript encuentra un error, Vercel también fallaría. Ambos deben terminar sin errores.

4. `git add`, `git commit`, `git push` a `main`.
5. Vercel publica `familia-monster` solo. Verifique (sección 10).

### 8.2 Añadir una pantalla nueva

1. `src/features/<modulo>/types.ts`: tipos de lo que responde la API.
2. `schemas.ts`: validación de formularios con Zod.
3. `api.ts`: consultas y mutaciones con TanStack Query, usando `api` de `client.ts` (nunca `fetch` directo).
4. `components/`: formularios y tarjetas, reutilizando `src/components/ui/`.
5. `<Modulo>Page.tsx`: la pantalla.
6. Registre la ruta en `src/app/router.tsx` y el enlace en `src/lib/navegacion.ts`.
7. Pruebas: schemas y formularios con Vitest (`*.test.ts` / `*.test.tsx`).

### 8.3 Reglas del frontend

- Montos siempre con `formatCOP`; los importes de formularios se normalizan con `pesos.ts`.
- Las operaciones que mueven dinero llevan `Idempotency-Key` (`useClaveIdempotencia`).
- Textos de la interfaz en español.
- Nada de secretos en el código ni en variables `VITE_`: todo lo que empiece con `VITE_` es público en el navegador.
- Colores solo desde los tokens de `theme.css`.
- `vercel.json` define los *rewrites* hacia la API y la política CSP. Si añade un recurso externo (fuente, imagen, script), debe permitirlo ahí; hoy todo es del mismo origen.

### 8.4 Cuando el backend cambia su contrato

Actualice juntos, en la misma rama: `types.ts`, `schemas.ts`, `api.ts` y los componentes que usen los campos. Pruebe con la API local antes de publicar. Orden de despliegue: ver 7.5.

### 8.5 Dependencias

- `package-lock.json` debe estar en Git: sin él, Vercel instala versiones distintas en cada despliegue.
- Revise alertas con `npm audit --omit=dev`. **No** use `npm audit fix --force`: sube versiones mayores y rompe código.
- Estado al 31/10/2026: alerta alta en `zod` (versión 3; el arreglo exige la 4, que es un cambio mayor y se programa aparte, con pruebas).

---

## 9. Si cambio X, ¿qué hago?

| Cambio | Migración | Qué publicar | Verificación |
|---|---|---|---|
| Regla de negocio en un `service.py` | No | Backend | `pytest`, luego `/api/v1/preparacion` |
| Consulta nueva en un `repository.py` | No | Backend | `pytest` |
| Columna o tabla nueva | Sí (7.2 y 7.3) | Backend, después de migrar | `pytest`, `alembic current` en Neon |
| Endpoint nuevo | No | Backend, luego frontend | `/api/docs` en local |
| Variable de entorno nueva | No | Redeploy del proyecto afectado | Logs de Vercel |
| Texto o estilo | No | Frontend | `npm run build` y `npm test` |
| Pantalla nueva | No | Frontend | Probar en local, luego en producción |
| Cambio de dominio del frontend | No | Actualizar `CORS_ORIGENES` en la API y `vercel.json` si cambia la API | Login desde el dominio nuevo |
| Rotar `SECRET_KEY` | No | Variable en Vercel, Redeploy | Las sesiones abiertas se cierran |
| Rotar la contraseña de Neon | No | `.env.neon` y `DATABASE_URL` en Vercel, Redeploy | `/api/v1/preparacion` |

---

## 10. Comprobación después de publicar

1. Estado **Ready** en el despliegue de Vercel.
2. `https://familia-monster.vercel.app/api/v1/preparacion` responde `"base_de_datos":"ok"` (atraviesa frontend, API y Neon).
3. Inicio de sesión con el administrador, recarga con F5 (sigue con sesión) y cierre de sesión.
4. Una operación pequeña en la función modificada.
5. Logs: en Vercel, proyecto afectado, menú **Logs**. Revise errores 5xx.
6. Si hubo migración: `alembic current` en Neon muestra la versión esperada.

Nota: `/preparacion` despierta la base de Neon y consume cómputo del plan gratuito. No la use con monitores que la consulten cada pocos minutos.

---

## 11. Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Login: "Origen no autorizado" (403) | `CORS_ORIGENES` no coincide con el dominio real del frontend | Corríjalo en la API y haga Redeploy |
| Al recargar vuelve al login | La cookie no viaja (dominio equivocado o `vercel.json` sin aplicar) | Entre siempre por el dominio del frontend; revise el rewrite |
| `/api/v1/preparacion` devuelve la página del frontend | El rewrite no se aplicó o el Root Directory está mal | Revise `frontend/vercel.json` y Settings del proyecto |
| `/api/v1/preparacion` devuelve 503 | La API no llega a Neon | Revise `DATABASE_URL` (con `-pooler`, sin comillas ni `DATABASE_URL=`) y los Logs |
| Primera visita lenta | Neon sale de su reposo y la función arranca en frío | Es normal; reintente |
| 500 en un reintento de pago | Falta la función de repositorio que devuelve el resultado original | Sección 6.6 |
| `npm run build` falla en Vercel pero no en local | Node o dependencias distintas | Compare versiones; confirme que `package-lock.json` está subido |
| Pantalla blanca tras publicar | La política CSP de `vercel.json` bloqueó un recurso | F12, pestaña Console: busque "Content Security Policy" |
| `pytest` con deadlocks o `no_autenticado` | Dos corridas a la vez sobre la misma base | Una sola terminal; desconecte pgAdmin |
| Una variable nueva no surte efecto | Vercel solo la aplica a despliegues nuevos | Redeploy |

---

## 12. Pendientes y mejoras recomendadas

- **Probar una recuperación real en Neon** (hoy solo se probó la restauración en una base local) y guardar copias fuera del computador.
- **Rol de solo lectura** en Neon para consultas SQL, en lugar de trabajar con `neondb_owner`.
- **Comprobantes:** requieren almacenamiento aparte; verificar límites y costos antes de activarlo.
- **Permisos entre roles en producción:** probar con un usuario `miembro`.
- **Alertas de `npm audit`:** actualizar `zod` a la versión 4 en una tarea aparte, con pruebas.
- **Peso del frontend:** el paquete principal supera 500 kB; se puede reducir con carga diferida de pantallas pesadas.
- **Avisos menores:** `Field(alias=...)` mal ubicado en esquemas de Pydantic, y el aviso de `httpx2` en las pruebas.
- **Verificar qué módulos del backend no se revisaron línea a línea** al redactar esta guía (`accounts`, `audit`, `reports`) antes de apoyarse en detalles de su comportamiento.

---

## 13. Documentos relacionados

- `docs/recuperacion.md`: copias de seguridad y recuperación.
- Instructivo de despliegue de cero a producción (PostgreSQL local, Neon, Vercel, primer hogar): si lo exporta a Markdown, guárdelo como `docs/instructivo-despliegue.md`.