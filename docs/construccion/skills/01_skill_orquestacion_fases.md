# Skill: Orquestación y fases (CHIQUISTRUKIS)

## Orden de implementación

1. Modelo Oracle + seeds (`institution`, `user_account`, `staff_member`).
2. Auth (login, sesión Redis, mapa de accesos).
3. Staff members CRUD.
4. Biometric import wizard (draft → rows → confirmation / cancellation).
5. `attendance_day` + panel de edición.
6. Justifications.
7. Reports annex-03/04.
8. Dashboard indicators.
9. Inconsistencies + gancho IA (stub al inicio).

## Reglas

- Respetar SB-04 (inglés en código/API/BD).
- No consolidar `attendance_day` hasta confirmation.
- No inventar campos fuera del modelo.
- Mutaciones relevantes → `audit_log`.
- Cierre de bloque: APROBADO | APROBADO CON OBSERVACIONES | BLOQUEADO.
