# Skill: Wizard carga biométrica (regla fija UX + API EN)

## Flujo UI (español en pantalla)

1. **Subir** archivo CSV/Excel → `POST /api/v1/biometric-imports` (`status=draft`).
2. **Una sola lista**, mismo orden del archivo:
   - Verde = DNI encontrado (editar + re-buscar).
   - Rojo = nuevo (Registrar / Omitir).
3. **Período detectado** → Cancelar o **Finalizar**.
4. **Finalizar** → `POST .../confirmation` → redirige a **Asistencia**.
5. Mes/archivo incorrecto → **Anular carga** `POST .../cancellation`.

## APIs (inglés)

- `POST /api/v1/biometric-imports` (multipart)
- `GET /api/v1/biometric-imports/{id}`
- `PATCH /api/v1/biometric-imports/{id}/rows/{rowId}` — action: `research` | `register_new` | `skip`
- `POST /api/v1/biometric-imports/{id}/confirmation`
- `POST /api/v1/biometric-imports/{id}/cancellation` `{ "reason": "..." }`
- `GET` historial de imports

## Reglas de negocio

- NO escribe `attendance_day` hasta confirmation.
- Filas nuevas sin resolver → 400 al confirmar.
- PATCH solo si `draft` (409 si no).
- Cancellation solo si `confirmed` (409 si no).
- Match por DNI; orden de filas = orden del archivo.
- Marcas originales no se pisan; correcciones auditadas.
