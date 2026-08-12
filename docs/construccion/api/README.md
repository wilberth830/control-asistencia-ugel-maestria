# API v1

- Contrato: `openapi_v1.yaml` (27 operaciones de dominio + health).
- Base path: `/api/v1/...` (inglés, SB-04).
- Auth: Bearer en Redis; pública solo `POST /api/v1/auth/sessions`.

Mapeo al documento Tema 5 (rutas ES históricas → EN):

| Tema 5 (ES) | Implementación |
|-------------|----------------|
| /api/auth/sesiones | /api/v1/auth/sessions |
| /api/personal | /api/v1/staff-members |
| /api/cargas-biometricas | /api/v1/biometric-imports |
| /api/asistencias | /api/v1/attendance-records |
| /api/justificaciones | /api/v1/justifications |
| /api/reportes/anexo-03 | /api/v1/reports/annex-03 |
| /api/dashboard/indicadores | /api/v1/dashboard/indicators |
