<!-- docs/recuperacion.md -->
<!-- Procedimiento de copia y recuperación de la base de datos de Familia Monster. -->
<!-- No contiene secretos: las URL reales viven solo en backend/.env.neon, que Git ignora. -->

# Copia de seguridad y recuperación

La base de datos de producción está en Neon (PostgreSQL). La ventana de restauración
gratuita de Neon es de solo 6 horas, por lo que NO sustituye a una copia propia.

## 1. Cuándo sacar una copia

- Una vez por semana.
- Antes de cualquier migración de Alembic contra Neon.
- Antes de cambios grandes (por ejemplo, importar datos).

## 2. Crear la copia

Desde `backend/`, con el entorno virtual activo. Si la terminal es nueva, agregue primero
`pg_dump` al PATH (la versión 18 está en `/c/Program Files/PostgreSQL/18/bin`).

    export PATH="$PATH:/c/Program Files/PostgreSQL/18/bin"

    python - <<'PY'
    import os, subprocess, datetime
    from dotenv import dotenv_values
    url = dotenv_values('.env.neon')['DATABASE_URL_MIGRACIONES']
    os.makedirs('../backups', exist_ok=True)
    nombre = '../backups/familia_monster_' + datetime.datetime.now().strftime('%Y%m%d_%H%M') + '.dump'
    resultado = subprocess.run(
        ['pg_dump', '--format=custom', '--no-owner', '--no-privileges', '--file', nombre, url],
        check=False,
    )
    print('codigo de salida:', resultado.returncode, '| archivo:', nombre)
    PY

Resultado esperado: `codigo de salida: 0`.

## 3. Comprobar que la copia es legible

    pg_restore --list ../backups/familia_monster_AAAAMMDD_HHMM.dump | head -20

Debe listar tablas como `users`, `households` y `transactions`.

## 4. Dónde guardarla

- La carpeta `backups/` y los archivos `*.dump` están en `.gitignore`: nunca se suben a GitHub.
- Guarde una copia fuera del computador (disco externo o almacenamiento personal cifrado).
- El archivo contiene datos financieros reales y el hash de la contraseña: trátelo como confidencial.

## 5. Probar la restauración (hacerlo de vez en cuando)

Siempre contra una base LOCAL desechable, nunca contra Neon.

    createdb -U postgres -h localhost familia_monster_restauracion
    pg_restore --no-owner --no-privileges -U postgres -h localhost \
      -d familia_monster_restauracion ../backups/familia_monster_AAAAMMDD_HHMM.dump
    psql -U postgres -h localhost -d familia_monster_restauracion \
      -c "SELECT (SELECT count(*) FROM users) AS usuarios, (SELECT count(*) FROM households) AS hogares;"
    dropdb -U postgres -h localhost familia_monster_restauracion

Última prueba exitosa: 31/10/2026 (1 usuario, 1 hogar, 1 integrante, 11 categorías, 1 registro de auditoría).

## 6. Recuperarse de un desastre en Neon

Estado: este procedimiento está descrito pero NO se ha probado contra Neon, solo contra una base local.

1. Si el error ocurrió hace menos de 6 horas, pruebe primero Backup & Restore en el panel de Neon.
2. Si no, cree una base vacía en Neon (nuevo proyecto o nueva rama) y obtenga su URL directa (sin "-pooler").
3. Restaure la copia más reciente en esa base vacía:

       pg_restore --no-owner --no-privileges -d "<URL_DIRECTA_NUEVA>" ../backups/familia_monster_AAAAMMDD_HHMM.dump

4. En Vercel, actualice `DATABASE_URL` con la URL CON pooler de la base nueva y haga Redeploy.
5. Verifique `/api/v1/preparacion` (debe responder `"base_de_datos":"ok"`) e inicie sesión.
6. Los datos posteriores a la última copia se pierden: por eso la frecuencia importa.