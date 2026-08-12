# Skill: Oracle — asistencia y trazabilidad

## Fuente de verdad

`attendance_day` (`staff_member_id` + `attendance_date` + `status` + `late_minutes` + `justification_id`).  
El mes se **calcula**; no hay tabla `attendance_month` persistida.

## Entidades (snake_case inglés)

`user_account`, `institution`, `staff_member`, `staff_institution`,  
`biometric_import` (`status`: draft|confirmed|cancelled; `period_start`/`period_end`),  
`biometric_mark`, `inconsistency`, `justification` (`support_file_path`, fechas),  
`attendance_day`, `audit_log`.

## Reglas

- `dni` UNIQUE 8 dígitos.
- Confirmación de import consolida `attendance_day`.
- Cancelación de import revierte marcas del archivo y recalcula el período.
- Justificación por rango actualiza días del rango.
- Baja lógica (`is_active` / `active` S-N); no borrar histórico.
- Fechas: DATE `YYYY-MM-DD`; TIMESTAMP con hora.
- FK con sufijo `_id`.
- No sobrescribir marcas originales: corrección deja trazabilidad en `audit_log`.

## Índices útiles

- `staff_member(dni)`, `attendance_day(staff_member_id, attendance_date)` UNIQUE,
  `biometric_import(status, period_start)`, `biometric_mark(biometric_import_id)`,
  `audit_log(entity_name, entity_id)`.
