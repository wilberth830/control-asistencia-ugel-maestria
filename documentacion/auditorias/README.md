# Auditorias

[Volver al indice principal](../README.md)

Esta seccion contiene auditorias tecnicas del repo y la regla para generar
nuevas auditorias.

## Documentos

| Documento | Descripcion |
|-----------|-------------|
| [Reglas de auditoria](reglas_auditoria.md) | Formato obligatorio, severidades y cierre de auditorias |
| [Auditoria completa historica](auditoria_completa.md) | Auditoria base generada sobre el estado inicial del proyecto |
| [Auditoria fullstack 2026-08-11](20260811_auditoria_fullstack.md) | Auditoria reciente del flujo frontend/backend/database |

## Como agregar una auditoria nueva

Guardar el archivo en esta carpeta con el formato:

```text
YYYYMMDD_auditoria_<alcance>.md
```

Ejemplo:

```text
20260811_auditoria_backend.md
```

Cada auditoria nueva debe enlazarse en la tabla de documentos y debe incluir
un enlace de regreso a este indice.
