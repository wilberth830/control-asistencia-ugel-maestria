# CHIQUISTRUKIS — scaffold con TEC-D01…D12

Todos los PBI técnicos del Tema 5 (§5.7) tienen **evidencia** en el repo (`docs/backlog_tec.md`).

| TEC | Qué hay |
|-----|---------|
| D01 | Capas frontend/backend/database/infra |
| D02 | SQL 10 tablas + seed |
| D03 | Login, bcrypt, sesión Redis, mapa access |
| D04 | OpenAPI + routers + apiClient front |
| D05 | Wizard import draft/confirm/cancel |
| D06 | Reglas inconsistencias + stub IA |
| D07 | Justificaciones + support path |
| D08 | attendance_day service |
| D09 | Annex 03/04 JSON |
| D10 | Dashboard indicators |
| D11 | audit_service |
| D12 | institution en reportes + seed |

## Demo local

```bash
# Redis aparte
cd infra/redis && docker compose up -d

cd ../../backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Login demo: director.demo / Demo12345
```

Persistencia Oracle: ejecutar `database/01_schema` + `02_seed` y cablear repositorios (hoy demo en memoria + Redis sesión).

Mockups: sube HTML a `disenos_base/`.


## Crear nuevo usuario 
user
ASISTENCIA_OWNER

sqlplus / as sysdba

ALTER SESSION SET CONTAINER = FREEPDB1;

CREATE USER asistencia_owner
IDENTIFIED BY "Asistencia123"
DEFAULT TABLESPACE USERS
TEMPORARY TABLESPACE TEMP
QUOTA UNLIMITED ON USERS;

GRANT CREATE SESSION TO asistencia_owner;
GRANT CREATE TABLE TO asistencia_owner;
GRANT CREATE VIEW TO asistencia_owner;
GRANT CREATE SEQUENCE TO asistencia_owner;
GRANT CREATE PROCEDURE TO asistencia_owner;
GRANT CREATE TRIGGER TO asistencia_owner;

sqlplus asistencia_owner/Asistencia123@localhost:1521/FREEPDB1

sqlplus asistencia_owner/Asistencia123@localhost:1521/FREEPDB1 @database/01_schema/01_create_tables.sql

sqlplus asistencia_owner/Asistencia123@localhost:1521/FREEPDB1 @database/01_schema/02_create_indexes.sql

sqlplus asistencia_owner/Asistencia123@localhost:1521/FREEPDB1 @database/02_seed/01_seed_demo.sql
sqlplus asistencia_owner/Asistencia123@localhost:1521/FREEPDB1 @database/03_checks/01_validate_database.sql

## Cómo ejecutar el proyecto

### 1. Base de datos Oracle

Configura tus parámetros locales copiando el ejemplo:

```cmd
copy database\00_configuracion\00_parametros.example.bat database\00_configuracion\00_parametros.local.bat
```

Edita `database\00_configuracion\00_parametros.local.bat` y coloca tu `DB_HOST`, `DB_PORT`, `DB_USER` y `DB_PASSWORD`.

Luego ejecuta el instalador indicando la PDB:

```cmd
ejecutar-bd.bat FREEPDB1
```

También puedes ejecutarlo sin parámetro y escribir la PDB cuando lo solicite:

```cmd
ejecutar-bd.bat
```

El instalador ejecuta en orden: schema, tablas, índices, seed y checks. Puede correrse varias veces sin duplicar datos.

### 3. Backend

cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

O bien desde la raíz del proyecto:

```powershell
cd scripts
.
start-backend.ps1
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir:

```text
http://127.0.0.1:5173
```

Usuario demo:

```text
director.demo / Demo12345
```
####XD