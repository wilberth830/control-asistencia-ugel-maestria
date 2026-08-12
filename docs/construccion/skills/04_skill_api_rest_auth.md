# Skill: API REST y autenticación

## Contrato + SB-04

- Paths y recursos en **inglés**, versionados: `/api/v1/...`
- Documentación de producto y UI en español.
- 27 operaciones de dominio (auth, staff, biometric-imports, inconsistencies, attendance, justifications, marks, reports, dashboard).

## Auth

- Pública: `POST /api/v1/auth/sessions`
- Resto: `Authorization: Bearer <token>` (Redis)
- Login → `token`, `role`, `access.modules`, `access.operations`
- Front usa mapa para menú; API aplica seguridad real

## Mapa de recursos (inglés)

| Recurso | Ejemplos |
|---------|----------|
| sessions | login, current, logout |
| staff-members | list, create, get, update, deactivate |
| biometric-imports | list, create (multipart), get, patch row, confirm, cancel |
| inconsistencies | list, review, correct |
| attendance-records | query month, update day |
| justifications | list, create, update, cancel |
| biometric-marks | correct |
| reports | annex-03, annex-04 (`format=json|xlsx`) |
| dashboard | indicators |

## Errores HTTP

200 · 201 · 400 · 401 · 403 · 404 · 409 (estado inválido, ej. confirmar no-draft)

## Notas

- Si existe OpenAPI previo con paths en español, migrar a inglés SB-04 o documentar alias; **nuevo código usa inglés**.
- operationId en camelCase inglés (`startSession`, `confirmBiometricImport`).
