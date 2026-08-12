# Auditoria tecnica - fullstack

> Repo: CHIQUISTRUKIS
> Fecha: 2026-08-11
> Modo: READ-ONLY sobre codigo operativo; solo se genera este reporte
> Alcance: fullstack
> Rama/commit: feature/build-project-with-codex / 40b2140

## Resumen ejecutivo

| Severidad | Cantidad | Descripcion |
|-----------|----------|-------------|
| Critico | 0 | No se encontro perdida inmediata de datos ni bloqueo total del sistema |
| Alto | 2 | Fallos reproducibles o respuestas falsas en flujos backend |
| Medio | 3 | Riesgos de contrato, rendimiento y arquitectura temporal |
| Bajo | 1 | Higiene de repositorio y reproducibilidad |

Estado: aprobado con observaciones.

El frontend compila, los checks de base pasan y la mayoria de pruebas backend
esta en verde. Sin embargo, la suite backend completa falla en reportes Excel
cuando no hay configuracion Oracle, y el modulo de inconsistencias puede devolver
exito aunque no haya persistencia real si Oracle falla.

## Hallazgos

### ERR-001 - Exportacion mensual falla sin Oracle configurado

| Campo | Valor |
|-------|-------|
| Severidad | Alto |
| Capa | backend |
| Archivo | `backend/app/services/report_service.py:94` |
| Estado | abierto |

**Problema**

`monthly_workbook()` consulta `biometric_repository.get_import(import_id)` cuando
recibe `import_id`, pero no captura `OracleRepositoryError`. En entorno de test
sin variables Oracle, el endpoint `/api/v1/reports/monthly-export` explota con
excepcion no controlada.

**Impacto**

El boton de descarga Excel puede fallar con error 500 si la conexion Oracle no
esta disponible o si el backend se ejecuta en modo memoria/demo. El JSON de
Anexo 03/04 puede funcionar, pero la descarga Excel queda fragil.

**Evidencia**

Prueba ejecutada:

```cmd
PYTHONPATH=. pytest backend/tests/unit
```

Resultado:

```text
1 failed, 39 passed
FAILED test_reports_dashboard_p6.py::test_monthly_export_accepts_import_id
OracleRepositoryError: Oracle connection settings are incomplete
```

La traza apunta a:

```text
backend/app/services/report_service.py:103
import_row = biometric_repository.get_import(import_id)
```

**Recomendacion**

Capturar `OracleRepositoryError` en `monthly_workbook()` y continuar sin
`file_name`, o resolver el import desde el servicio de cargas para mantener
compatibilidad con modo memoria/test.

### ERR-002 - Inconsistencias puede devolver exito sin persistir cambios

| Campo | Valor |
|-------|-------|
| Severidad | Alto |
| Capa | backend |
| Archivo | `backend/app/services/inconsistency_service.py:41` |
| Estado | abierto |

**Problema**

`review()` y `correct()` delegan a `_set_status()`. Si Oracle falla,
`_set_status()` devuelve un objeto sintetico:

```text
{"id": inconsistency_id, "status": status}
```

sin confirmar que la inconsistencia exista ni que el cambio se haya guardado.

**Impacto**

La UI o una integracion podria creer que una inconsistencia fue revisada o
corregida cuando en realidad no se persistio nada. Es un falso positivo de
mutacion.

**Evidencia**

Referencias:

```text
backend/app/services/inconsistency_service.py:49
backend/app/services/inconsistency_service.py:50
```

El repositorio real si distingue fila inexistente:

```text
backend/app/repositories/inconsistency_repository.py:47
return None
```

pero esa garantia se pierde cuando ocurre `OracleRepositoryError`.

**Recomendacion**

En mutaciones, no devolver exito si la persistencia falla. Responder 503 o
mantener un store transaccional alternativo real.

### ERR-003 - OpenAPI no documenta descarga mensual Excel

| Campo | Valor |
|-------|-------|
| Severidad | Medio |
| Capa | api |
| Archivo | `docs/api/openapi_v1.yaml` |
| Estado | abierto |

**Problema**

Backend y frontend usan:

```text
GET /api/v1/reports/monthly-export
```

pero el contrato OpenAPI solo lista `annex-03` y `annex-04` dentro de reportes.

**Impacto**

El contrato queda incompleto para QA, integraciones y revision academica. Una
persona que siga el OpenAPI no sabra que existe la descarga Excel.

**Evidencia**

Uso en frontend:

```text
frontend/src/App.tsx:2289
```

Ruta backend:

```text
backend/app/api/reports.py:12
```

Busqueda en OpenAPI:

```text
annex-03 encontrado
annex-04 encontrado
monthly-export no encontrado
```

**Recomendacion**

Agregar `/api/v1/reports/monthly-export` al OpenAPI con parametros `month`,
`year`, `import_id` opcional y respuesta
`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

### ERR-004 - Asistencia carga todos los imports confirmados

| Campo | Valor |
|-------|-------|
| Severidad | Medio |
| Capa | performance |
| Archivo | `frontend/src/App.tsx:1466` |
| Estado | abierto |

**Problema**

La pantalla de Carga biometrica ya limita historial a 10, pero la pantalla de
Asistencia sigue llamando:

```text
GET /api/v1/biometric-imports
```

sin `status`, `month`, `year` ni `limit`, y luego filtra confirmados en el
cliente.

**Impacto**

Con miles de cargas, entrar a Asistencia puede volverse lento aunque el usuario
solo necesite archivos de un mes. El costo de red y render crece con todo el
historico.

**Evidencia**

Referencia:

```text
frontend/src/App.tsx:1466
importsResponse.data.filter((item) => item.status === "confirmed")
```

**Recomendacion**

Solicitar imports por mes/estado desde backend o cargar inicialmente solo el
rango necesario. Ejemplo:

```text
GET /api/v1/biometric-imports?status=confirmed&month=8&year=2026
```

### ERR-005 - Sesiones Redis desactivadas por codigo

| Campo | Valor |
|-------|-------|
| Severidad | Medio |
| Capa | backend/security |
| Archivo | `backend/app/services/session_store.py:22` |
| Estado | abierto |

**Problema**

`SessionStore.USE_REDIS = False` fuerza sesiones en memoria cuando
`app_allow_memory_session` esta habilitado. Esto contradice la regla de
arquitectura original donde Bearer usa Redis.

**Impacto**

En desarrollo compartido puede ocultar errores de Redis. En un despliegue con
mas de un proceso, las sesiones no serian compartidas y se perderian al
reiniciar el backend.

**Evidencia**

Referencias:

```text
backend/app/services/session_store.py:22
backend/app/services/session_store.py:68
backend/app/services/session_store.py:101
```

**Recomendacion**

Mantener memoria solo como modo local explicito y documentado. Para integracion
del equipo, volver a una bandera de configuracion o perfil de entorno antes de
despliegue.

### ERR-006 - Archivos de sustento quedan como untracked

| Campo | Valor |
|-------|-------|
| Severidad | Bajo |
| Capa | security/repo |
| Archivo | `.gitignore` |
| Estado | abierto |

**Problema**

`backend/storage/` aparece como carpeta no versionada con archivos de sustento,
pero `.gitignore` no ignora `backend/storage/` ni `backend/storage/support_files/`.

**Impacto**

Existe riesgo de commitear documentos o imagenes subidas por usuarios durante
pruebas. Tambien ensucia el estado del repo y dificulta revisar cambios reales.

**Evidencia**

Estado del repo antes de la auditoria:

```text
?? backend/storage/
```

El servicio guarda archivos en:

```text
backend/app/services/support_file_service.py:58
backend/app/services/support_file_service.py:60
```

**Recomendacion**

Agregar `backend/storage/` al `.gitignore` o mover uploads a una carpeta local
ignorada por defecto. Mantener solo `.gitkeep` si se necesita conservar la
estructura.

## Pruebas revisadas

Backend:

```cmd
PYTHONPATH=. pytest backend/tests/unit
```

Resultado:

```text
1 failed, 39 passed
```

Frontend:

```cmd
cd frontend
npm run build
```

Resultado:

```text
build OK
```

Base de datos:

```cmd
python database/03_checks/check_p1_static.py
python database/03_checks/check_idempotency.py
```

Resultado:

```text
P1 static database checks passed
Idempotency static checks passed
```

## Riesgos residuales

- La auditoria no ejecuto pruebas end-to-end con navegador real.
- No se valido una corrida completa con Redis activo porque Redis esta
  desactivado en codigo.
- No se verifico contenido de `.env` para evitar exponer secretos en el reporte.
- Hay cambios no commiteados previos a la auditoria en frontend/backend; el
  resultado corresponde al estado local actual.

## Siguientes pasos sugeridos

1. Corregir `monthly_workbook()` para no fallar cuando Oracle no esta disponible
   y volver a correr toda la suite backend.
2. Cambiar mutaciones de inconsistencias para que fallen con 503 si no pueden
   persistir.
3. Actualizar OpenAPI con `/api/v1/reports/monthly-export`.
4. Optimizar carga inicial de Asistencia para consultar imports por mes/estado.
5. Ignorar `backend/storage/` en Git antes de subir archivos de prueba.

Estado: aprobado con observaciones.
