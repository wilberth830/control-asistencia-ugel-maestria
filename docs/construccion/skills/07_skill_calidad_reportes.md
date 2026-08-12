# Skill: Calidad, auditoría y reportes MINEDU

## Atributos

Seguridad (token+RBAC) · Fiabilidad (flujo import+Oracle) · Usabilidad (wizard/panel) ·
Eficiencia (Redis) · Mantenibilidad (capas/módulos) · **SB-04** (lint, tests, DoD)

## Auditoría

Crear, editar, anular, confirmar import, corregir marca/inconsistencia → `audit_log`.

## Anexos

- Annex 03: matriz diaria desde `attendance_day` + cabecera `institution`.
- Annex 04: totales del mes.
- Query `format=json|xlsx` (json = preview UI).

## IA

Detección de inconsistencias **interna**. Estados: pending | reviewed | corrected.  
IA no aprueba justificaciones ni modifica registros sola (SB-04).

## Quality gate (merge)

Frontend: Prettier, ESLint, tests, build.  
Backend: Black, Ruff, pytest.  
BD: migración + constraints. Docs actualizadas. PR revisado.
