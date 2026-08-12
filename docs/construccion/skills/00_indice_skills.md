# Skills — CHIQUISTRUKIS (Control de Asistencia Biométrica)

## Objetivo

Guiar la implementación del MVP: React → API REST → Python → Oracle/Redis + IA,
alineado a Tema 5, OpenAPI, mockups y **SB-04 Normas de codificación**.

## Catálogo

| # | Skill | Dominio |
|---|--------|---------|
| 01 | [Orquestación y fases](01_skill_orquestacion_fases.md) | Proceso |
| 02 | [Arquitectura en capas y módulos](02_skill_arquitectura_modulos.md) | Diseño |
| 03 | [Oracle asistencia y trazabilidad](03_skill_oracle_asistencia.md) | Datos |
| 04 | [API REST y autenticación](04_skill_api_rest_auth.md) | Backend |
| 05 | [Wizard carga biométrica](05_skill_wizard_carga.md) | Dominio crítico |
| 06 | [UI admin y flujos UX](06_skill_ui_ux_admin.md) | Frontend |
| 07 | [Calidad, auditoría y reportes MINEDU](07_skill_calidad_reportes.md) | Calidad / Anexos |
| 08 | [Normas de codificación SB-04](08_skill_normas_codificacion.md) | Convenciones |

## Precedencia

1. Tema 5 + reglas de diseño (wizard, panel 90/10, anular carga).
2. SB-04: código/API/BD en **inglés**; UI, docs y commits en **español**.
3. Contrato API (paths en inglés versionados `/api/v1/...` según SB-04; mapear operationIds del diseño).
4. Modelo de datos (`attendance_day` / asistencia_dia = fuente de verdad).
5. Skills de dominio.

## Stack fijo

Front React + TypeScript · Backend Python + FastAPI · Oracle · Redis · IA solo inconsistencias (interna).
