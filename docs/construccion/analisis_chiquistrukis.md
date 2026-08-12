# Análisis Estructural: CHIQUISTRUKIS (Control de Asistencia)

Este documento resume la arquitectura, estructura y flujos de ejecución del proyecto `control-asistencia-ugel-maestria`, basado en el análisis de la rama `feature/build-project-with-codex`.

## 1. Stack Tecnológico

- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI
- **Base de Datos**: Oracle (scripts SQL para creación de esquema)
- **Caché/Sesión**: Redis (desactivado en la rama actual en favor de una sesión en memoria para desarrollo).
- **Tooling**: Codex (agentes para guiar el desarrollo), `ruff` y `black` para linting/formato en Python.

---

## 2. Diagrama de Ejecución: Cómo Levantar el Sistema

```mermaid
graph TD
    subgraph A[PASO 0: Prerequisitos]
        direction LR
        A1[Node 18+]
        A2[Python 3.11+]
        A3[Oracle DB 21c/FREE]
        A4[(Redis - Opcional)]
    end

    subgraph B[PASO 1: Base de Datos Oracle]
        direction LR
        B1["cd database/"]
        B2["ejecutar-bd.bat o SQLs manuales"]
        B3["Resultado: Esquema 'ASISTENCIA' listo en PDB"]
    end

    subgraph C[PASO 2: Backend FastAPI]
        direction LR
        C1["cd backend/"]
        C2["pip install -r requirements.txt"]
        C3[".env con credenciales Oracle"]
        C4["uvicorn app.main:app --reload"]
        C5["API disponible en http://localhost:8000"]
    end

    subgraph D[PASO 3: Frontend React]
        direction LR
        D1["cd frontend/"]
        D2["npm install"]
        D3[".env con VITE_API_BASE_URL"]
        D4["npm run dev"]
        D5["UI disponible en http://localhost:5173"]
    end

    A --> B --> C --> D
```

---

## 3. Arquitectura del Backend (FastAPI)

El backend sigue una arquitectura en capas, centrada en servicios que encapsulan la lógica de negocio.

```mermaid
graph TD
    subgraph "API Layer (app/api)"
        direction LR
        R_AUTH["auth.py"]
        R_STAFF["staff_members.py"]
        R_BIO["biometric_imports.py"]
        R_ATT["attendance.py"]
        R_DASH["dashboard.py"]
        R_REP["reports.py"]
    end

    subgraph "Service Layer (app/services)"
        S_AUTH["auth_service.py"]
        S_STAFF["staff_member_service.py"]
        S_BIO["biometric_import_service.py"]
        S_ATT["attendance_service.py"]
        S_DASH["dashboard_service.py"]
        S_REP["report_service.py"]
        S_AUDIT["audit_service.py"]
    end

    subgraph "Core/Infra (app/core, app/rules)"
        C_SEC["security.py"]
        C_CONF["config.py (.env)"]
        C_RULES["inconsistency_rules.py"]
        C_DEPS["deps.py (DI)"]
    end

    R_AUTH --> C_DEPS --> S_AUTH --> C_SEC
    R_STAFF --> C_DEPS --> S_STAFF --> S_AUDIT
    R_BIO --> C_DEPS --> S_BIO --> S_STAFF
    R_ATT --> C_DEPS --> S_ATT
    R_DASH --> C_DEPS --> S_DASH
    R_REP --> C_DEPS --> S_REP

    S_DASH --> S_ATT
    S_DASH --> S_BIO
    S_DASH --> S_STAFF

    S_REP --> S_ATT
    S_REP --> S_STAFF
```
**Puntos Clave:**
- **`deps.py`** centraliza la inyección de dependencias (como la autenticación de usuario) para todos los endpoints.
- **`attendance_service.py`** es el núcleo; `dashboard` y `reports` dependen de él.
- **`audit_service.py`** es utilizado por todos los servicios que realizan mutaciones para mantener un registro de cambios.

---

## 4. Modelo de Datos (Oracle)

El esquema de la base de datos está normalizado y centrado en las entidades `staff_member` y `attendance_day`.

```mermaid
erDiagram
    USER_ACCOUNT {
        int id PK
        varchar username
        varchar password_hash
        varchar role_name
    }

    STAFF_MEMBER {
        int id PK
        varchar dni UK
        varchar last_names
        varchar first_names
    }

    INSTITUTION {
        int id PK
        varchar ugel
        varchar school_name
        varchar modular_code
    }

    BIOMETRIC_IMPORT {
        int id PK
        varchar file_name
        varchar status
        int user_account_id FK
    }

    BIOMETRIC_MARK {
        int id PK
        datetime marked_at
        varchar mark_type
        int staff_member_id FK
        int biometric_import_id FK
    }

    INCONSISTENCY {
        int id PK
        varchar issue_type
        varchar status
        int mark_id FK
    }

    JUSTIFICATION {
        int id PK
        date start_date
        date end_date
        varchar reason
        int staff_member_id FK
        int registered_by_id FK
    }

    ATTENDANCE_DAY {
        int id PK
        date attendance_date
        varchar status
        int late_minutes
        int staff_member_id FK
        int justification_id FK
    }

    AUDIT_LOG {
        int id PK
        varchar entity_name
        int entity_id
        varchar action_name
        int user_account_id FK
    }

    STAFF_INSTITUTION {
        int id PK
        int staff_member_id FK
        int institution_id FK
    }

    USER_ACCOUNT ||--o{ BIOMETRIC_IMPORT : "uploads"
    USER_ACCOUNT ||--o{ AUDIT_LOG : "performs"
    USER_ACCOUNT ||--o{ JUSTIFICATION : "registers"
    STAFF_MEMBER ||--o{ BIOMETRIC_MARK : "has"
    STAFF_MEMBER ||--o{ ATTENDANCE_DAY : "has"
    STAFF_MEMBER ||--o{ JUSTIFICATION : "applies_to"
    STAFF_MEMBER ||--o{ STAFF_INSTITUTION : "belongs_to"
    INSTITUTION ||--o{ STAFF_INSTITUTION : "has"
    BIOMETRIC_IMPORT ||--o{ BIOMETRIC_MARK : "contains"
    BIOMETRIC_MARK ||--o{ INCONSISTENCY : "can_have"
    JUSTIFICATION }o--|| ATTENDANCE_DAY : "explains"

```
**Fuente de Verdad**: La tabla `ATTENDANCE_DAY` es la fuente canónica de la asistencia diaria de una persona. El resto de las tablas (marcas, importaciones, justificaciones) alimentan o explican el estado de esta tabla.

---

## 5. Flujo Crítico: Wizard de Importación Biométrica

Este es el flujo de negocio más complejo y central del sistema.

```mermaid
sequenceDiagram
    participant FE as Frontend (UI)
    participant BE as Backend (API)
    participant DB as Oracle DB

    FE->>BE: POST /api/v1/biometric-imports (upload file)
    BE->>DB: INSERT INTO biometric_import (status='draft')
    BE-->>FE: {import_id, rows_to_review}

    loop Revisión Manual
        FE->>BE: PATCH /api/v1/biometric-imports/{id}/rows/{row_id} (correction)
        BE-->>FE: {ack}
    end

    alt Confirmar Carga
        FE->>BE: POST /api/v1/biometric-imports/{id}/confirmation
        BE->>DB: UPDATE biometric_import SET status='confirmed'
        BE->>DB: INSERT INTO biometric_mark
        BE->>DB: (Run inconsistency_rules) INSERT INTO inconsistency
        BE->>DB: (Calculate) INSERT/UPDATE attendance_day
        BE-->>FE: {status: "processed"}
    else Cancelar Carga
        FE->>BE: POST /api/v1/biometric-imports/{id}/cancellation
        BE->>DB: UPDATE biometric_import SET status='cancelled'
        BE-->>FE: {status: "cancelled"}
    end
```

---

## 6. Mapa de Capas y Carpetas

| Capa Lógica     | Carpeta Física        | Agente Responsable (Codex) |
|-----------------|-----------------------|----------------------------|
| **Presentación**| `frontend/`           | `frontend_react`           |
|                 | `disenos_base/`       | (Referencia para UI/UX)    |
| **API/Negocio** | `backend/app/api/`    | `backend_api`              |
|                 | `backend/app/services/`| `backend_api`              |
|                 | `backend/app/rules/`  | `backend_api`              |
| **Datos**       | `database/`           | `oracle_dba`               |
| **Infra**       | `infra/redis/`        | `ops` / `architect`        |
| **Testing**     | `backend/tests/`      | `qa_tester`                |
| **Docs**        | `docs/`               | `architect`                |

