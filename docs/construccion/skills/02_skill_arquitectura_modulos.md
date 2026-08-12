# Skill: Arquitectura en capas y módulos

## Capas

Presentación (React) → API REST → Lógica Python → Datos (Oracle + Redis) → IA (apoyo)

## Módulos

1. Seguridad y acceso — login, logout, sesión Redis, RBAC, mapa accesos
2. Personal — CRUD + baja lógica
3. Asistencia biométrica — upload, match DNI, verde/rojo, período, confirmar, anular, inconsistencias
4. Administración de asistencia — grilla Anexo 03, panel día, justificaciones
5. Reportes oficiales — vista previa + export Anexo 03/04
6. Dashboard — totales + distribución marcaciones

## Backend

Router → Service → Repository → Oracle. Token en Redis. Sin SQL en controladores.
