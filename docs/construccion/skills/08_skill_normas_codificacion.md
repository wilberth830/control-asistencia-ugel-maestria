# Skill: Normas de codificación (SB-04)

## Regla principal

| Ámbito | Idioma |
|--------|--------|
| Código, API, base de datos | **Inglés** |
| Interfaz de usuario, documentación, mensajes de commit | **Español** |

## Nomenclatura

| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| Componentes React | PascalCase | `AttendanceTable.tsx` |
| Variables/funciones TS | camelCase | `calculateLateMinutes` |
| Python funciones/módulos | snake_case | `calculate_late_minutes` |
| Clases Python/TS | PascalCase | `AttendanceService` |
| Constantes | UPPER_SNAKE_CASE | `MAX_UPLOAD_SIZE_MB` |
| Tablas y columnas | snake_case | `biometric_mark`, `staff_member_id` |
| FK | sufijo `_id` | `staff_member_id` |

- Sin tildes, espacios ni caracteres especiales en identificadores técnicos.
- Mismo término en front, back, API y BD (glosario único).
- Nunca contraseñas, tokens ni secretos en el código.

## Estructura de carpetas

```
frontend/src/
  components/  features/  pages/  services/  tests/
backend/app/
  api/  models/  schemas/  services/  rules/  tests/
database/          # scripts Oracle / migraciones
docs/              # CODING_STANDARDS.md, arquitectura
```

Responsabilidad: rutas reciben; services aplican lógica; repositories acceden a datos; rules procesan asistencia.

## API

- REST en **plural** y **versionadas**: `/api/v1/staff-members`, `/api/v1/biometric-imports`.
- Códigos: 200 éxito, 201 creación, 400 inválido, 401/403 auth, 404, 409 conflicto.
- No sobrescribir marcas biométricas originales (corrección con trazabilidad).

### Glosario EN (código) ↔ dominio ES (UI/docs)

| Inglés (código/API/BD) | Español (UI / docs) |
|------------------------|---------------------|
| staff_member / staff-members | personal |
| biometric_import / biometric-imports | carga biométrica |
| attendance_day / attendance-records | asistencia (día) |
| justification | justificación |
| inconsistency | inconsistencia |
| institution | institución |
| annex-03 / annex-04 | Anexo 03 / 04 |
| session | sesión |

## Seguridad

- Solo hashes de contraseña.
- `.env`, `node_modules`, `__pycache__`, `.venv` fuera de Git.
- Validar tipo, tamaño y contenido de archivos importados.
- Acceso por institución y rol.
- Auditoría: quién, cuándo, qué cambió y motivo.
- IA solo sugiere inconsistencias; **no** aprueba justificaciones ni modifica sola.

## Git

| Elemento | Convención | Ejemplo |
|----------|------------|---------|
| Rama | `tipo/id-descripcion` | `feature/hu-03-biometric-import` |
| Commit | `tipo(ambito): mensaje` en español | `feat(import): agrega carga de CSV` |
| Integración | PR obligatorio + revisión de otro integrante | |

No trabajar directo en `main`. Commits pequeños y con propósito.

## Calidad antes de merge

| Capa | Checks |
|------|--------|
| Frontend | Prettier · ESLint · tests · build |
| Backend | Black · Ruff · pytest |
| BD | migración + restricciones |
| Docs | README / técnico actualizado |

## Escenarios de prueba mínimos

- Login válido / inválido
- DNI duplicado
- Archivo biométrico inválido o filas erróneas
- Marcas duplicadas, incompletas, fechas inválidas
- Tardanzas y justificaciones
- Correcciones con trazabilidad
- Confirmación de carga crea `attendance_day`; anulación revierte

## Definition of Done

Criterios de aceptación · convenciones SB-04 · sin secretos · lint/format/tests/build · revisión de par · docs actualizadas · aceptación PO.
