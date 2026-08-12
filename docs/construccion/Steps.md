Actúa como orquestador del repo CHIQUISTRUKIS.
Lee AGENTS.md, docs/backlog_tec.md, docs/skills/00_indice_skills.md y docs/api/openapi_v1.yaml.

Reglas:
1) Avanza SOLO un paso a la vez (orden abajo).
2) Al TERMINAR cada paso: escribe qué cambió, cómo probarlo, ejecuta la prueba (o indica el comando exacto), y si falla CORRIGE hasta que pase.
3) No pases al paso N+1 si el N no está en verde.
4) Un agente solo escribe en su carpeta (oracle_dba→database/, backend_api→backend/, frontend_react→frontend/).
5) Redis se levanta aparte (infra/redis). Código/API/BD en inglés; UI en español.

Orden de pasos:
P1 Schema Oracle + seed (demo user)
P2 Auth: login + sesión Redis + /health
P3 Staff members CRUD según OpenAPI
P4 Biometric import wizard (draft/confirm/cancel)
P5 Attendance day + justifications
P6 Reports annex-03/04 JSON + dashboard
P7 Frontend: login + rutas básicas alineadas a disenos_base/

Empieza SOLO por P1. Al terminar: prueba + corrección. Espera mi “OK” o continúa si la prueba pasó.

Si la prueba del paso pasa, continúa al siguiente automáticamente.