# database/ — Capa Oracle

Objetos en **inglés** (SB-04). El despliegue de base de datos debe ser idempotente: una ejecución o N ejecuciones dejan el mismo estado final, sin duplicar seed ni destruir datos existentes.

## Carpetas

- `00_configuracion/` — configuración de PDB/schema y parámetros locales.
- `01_schema/` — tablas, constraints e índices.
- `02_seed/` — institución, usuario demo y personal demo.
- `03_checks/` — verificaciones estáticas de estructura e idempotencia.

## Ejecución

Desde la raíz del repo:

```cmd
ejecutar-bd.bat FREEPDB1
```

O en modo interactivo:

```cmd
ejecutar-bd.bat
```

El instalador solicita la PDB si no se pasa por argumento. La contraseña no debe versionarse ni imprimirse.

## Parámetros locales

Copiar:

```text
database/00_configuracion/00_parametros.example.bat
```

como:

```text
database/00_configuracion/00_parametros.local.bat
```

`00_parametros.local.bat` está ignorado por Git y puede definir:

```bat
set "DB_HOST=localhost"
set "DB_PORT=1521"
set "DB_USER=ASISTENCIA_OWNER"
set "DB_PASSWORD=..."
```

Si `DB_PASSWORD` no está definido, `ejecutar-bd.bat` lo pedirá en consola sin mostrarlo.

## Orden de ejecución

1. Configurar PDB y schema: `00_configuracion/00_create_schema.sql`.
2. Crear/validar tablas y constraints: `01_schema/01_create_tables.sql`.
3. Crear/validar índices: `01_schema/02_create_indexes.sql`.
4. Ejecutar seed demo: `02_seed/01_seed_demo.sql`.
5. Ejecutar checks: `03_checks/check_p1_static.py` y `03_checks/check_idempotency.py`.

## Entidades

`user_account`, `institution`, `staff_member`, `staff_institution`, `biometric_import`, `biometric_mark`, `inconsistency`, `justification`, `attendance_day` (**fuente de verdad**), `audit_log` y `ai_usage_log`.

## Reglas de seguridad

- No usar `GRANT DBA`.
- No versionar contraseñas reales.
- No imprimir cadenas completas `usuario/password@host:port/PDB`.
- No usar `DROP TABLE`, `DROP USER`, `DROP SEQUENCE` ni limpieza destructiva para lograr idempotencia.


sqlplus ASISTENCIA_OWNER/Asistencia123@localhost:1521/FREEPDB1 @database/04_maintenance/01_clear_uploaded_data.sql
