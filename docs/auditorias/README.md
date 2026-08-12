# Auditorias tecnicas del repo

Esta carpeta guarda las auditorias generadas para CHIQUISTRUKIS.

La auditoria historica base del proyecto esta en:

```text
docs/AUDITORIA_COMPLETA.md
```

Las nuevas auditorias deben guardarse en esta carpeta con nombres fechados:

```text
docs/auditorias/YYYYMMDD_auditoria_<alcance>.md
```

Ejemplos:

```text
docs/auditorias/20260811_auditoria_backend.md
docs/auditorias/20260811_auditoria_frontend.md
docs/auditorias/20260811_auditoria_database.md
docs/auditorias/20260811_auditoria_fullstack.md
```

## Regla para generar auditorias

Toda auditoria debe ejecutarse en modo revision. Por defecto no debe modificar
codigo, base de datos, configuracion ni archivos operativos. Si durante la
auditoria se detecta una correccion necesaria, primero se documenta el hallazgo
y luego se espera autorizacion explicita para implementar.

La auditoria debe revisar el estado real del repo, no asumir que la documentacion
esta actualizada. Antes de emitir conclusiones, debe leer los archivos fuente,
contratos API, scripts SQL y pruebas relacionadas con el alcance.

## Alcances permitidos

- `backend`: API, servicios, repositorios, autenticacion, sesiones, reglas de negocio.
- `frontend`: pantallas, rutas, estados, llamadas API, UX y errores visibles.
- `database`: schema Oracle, indices, seed, scripts de mantenimiento e idempotencia.
- `api`: OpenAPI, consistencia entre contrato, backend y frontend.
- `fullstack`: flujo completo de usuario entre frontend, backend y base de datos.
- `security`: secretos, credenciales, tokens, permisos, CORS y datos sensibles.
- `performance`: consultas, paginacion, payloads, tiempos de carga y cuellos de botella.

## Formato obligatorio

Cada auditoria debe usar esta estructura:

```md
# Auditoria tecnica - <alcance>

> Repo: CHIQUISTRUKIS
> Fecha: YYYY-MM-DD
> Modo: READ-ONLY
> Alcance: <backend|frontend|database|api|fullstack|security|performance>
> Rama/commit: <rama o commit revisado>

## Resumen ejecutivo

| Severidad | Cantidad | Descripcion |
|-----------|----------|-------------|
| Critico | 0 | Rompe funcionalidad principal, datos o seguridad |
| Alto | 0 | Flujo incompleto, regresion importante o riesgo operativo |
| Medio | 0 | Defecto parcial, UX confusa, validacion incompleta |
| Bajo | 0 | Documentacion, limpieza, cobertura o deuda menor |

## Hallazgos

### ERR-001 - <titulo corto>

| Campo | Valor |
|-------|-------|
| Severidad | Critico/Alto/Medio/Bajo |
| Capa | backend/frontend/database/api/security/performance |
| Archivo | `ruta/archivo.ext:linea` |
| Estado | abierto/corregido/no aplica |

**Problema**

Descripcion concreta del error o riesgo.

**Impacto**

Que se rompe, a quien afecta y en que escenario.

**Evidencia**

Fragmento corto, ruta, endpoint, SQL o comportamiento observado.

**Recomendacion**

Accion sugerida sin implementar cambios automaticamente.

## Pruebas revisadas

- Comando ejecutado o razon por la que no se ejecuto.
- Resultado observado.

## Riesgos residuales

- Riesgos que quedan pendientes aunque no sean bloqueantes.

## Siguientes pasos sugeridos

1. Accion recomendada.
2. Accion recomendada.
```

## Criterios de severidad

`Critico`: perdida de datos, bloqueo del flujo principal, vulnerabilidad grave,
credenciales expuestas o API inutilizable.

`Alto`: funcionalidad importante incompleta, endpoint desconectado, persistencia
incorrecta, validacion que permite datos inconsistentes o lentitud severa.

`Medio`: errores parciales, comportamiento confuso, falta de paginacion,
mensajes poco claros, cobertura insuficiente en flujos relevantes.

`Bajo`: mejoras de documentacion, nombres, pequenos ajustes visuales, limpieza o
deuda tecnica sin impacto inmediato.

## Comandos sugeridos

Backend:

```cmd
cd backend
pytest
```

Frontend:

```cmd
cd frontend
npm run build
```

Base de datos:

```cmd
python database/03_checks/check_p1_static.py
python database/03_checks/check_idempotency.py
```

## Regla de cierre

Una auditoria termina con una conclusion clara:

```text
Estado: aprobado / aprobado con observaciones / no aprobado
```

Si hay hallazgos criticos abiertos, el estado debe ser `no aprobado`.
Si hay hallazgos altos abiertos, el estado debe ser como minimo
`aprobado con observaciones`.
