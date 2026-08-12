# PBIs técnicos (Tema 5 §5.7) — evidencia en el repo

Estado: **Listo en diseño/scaffold** = estructura, contrato y código base presentes.  
La lógica completa de negocio se completa al conectar Oracle real y subir mockups a `disenos_base/`.

| Código | Descripción | Evidencia en repo | Estado |
|--------|-------------|-------------------|--------|
| **TEC-D01** | Estructura de capas (React, API, Python, datos) | `frontend/`, `backend/`, `database/`, `infra/redis/`, `docs/architecture/` | Cumple |
| **TEC-D02** | Modelo de datos Oracle (todas las entidades) | `database/01_schema/01_create_tables.sql`, `docs/data_model.md` | Cumple |
| **TEC-D03** | Seguridad: login, hash, sesión Redis, roles | `backend/app/services/auth_service.py`, `session_store.py`, `api/auth.py` | Cumple (scaffold + demo en memoria si no hay Oracle) |
| **TEC-D04** | API REST base + conexión Front | `docs/api/openapi_v1.yaml`, `backend/app/api/*`, `frontend` Axios base | Cumple estructura |
| **TEC-D05** | Importación CSV/Excel biométrico | `backend/app/services/biometric_import_service.py`, `api/biometric_imports.py`, skill 05 | Cumple contrato + stub flujo draft |
| **TEC-D06** | Motor inconsistencias + IA | `backend/app/rules/inconsistency_rules.py`, `services/inconsistency_service.py` | Cumple reglas + stub IA |
| **TEC-D07** | Justificaciones + archivo sustento | `api/justifications.py`, `services/justification_service.py` | Cumple contrato |
| **TEC-D08** | Consolidación diaria attendance_day | `services/attendance_service.py`, schema `attendance_day` | Cumple modelo + servicio |
| **TEC-D09** | Generador Anexo 03 y 04 | `services/report_service.py`, `api/reports.py` | Cumple JSON; XLSX marcable |
| **TEC-D10** | Indicadores Dashboard | `services/dashboard_service.py`, `api/dashboard.py` | Cumple contrato |
| **TEC-D11** | Auditoría transversal | `services/audit_service.py`, tabla `audit_log` | Cumple |
| **TEC-D12** | Parámetros institución (cabecera reportes) | tabla `institution`, uso en `report_service` | Cumple |

## Definition of Done por TEC (implementación)

- Contrato OpenAPI o schema SQL existe.
- Módulo/servicio o script referenciado en esta tabla.
- Sin secretos en código.
- Comentario o docstring enlaza el código TEC-Dxx.
