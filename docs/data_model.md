# Modelo de datos (Tema 5 → implementación)

Fechas: `YYYY-MM-DD`. Timestamp: `YYYY-MM-DD HH:MM:SS`.  
Fuente de verdad de asistencia: **`attendance_day`** (el mes se calcula).

## Glosario ES (Tema 5) ↔ EN (código/BD)

| Tema 5 (ES) | Código / BD (EN) |
|-------------|------------------|
| usuario | user_account |
| institucion | institution |
| personal | staff_member |
| personal_institucion | staff_institution |
| archivo_carga | biometric_import |
| marca_biometrica | biometric_mark |
| inconsistencia | inconsistency |
| justificacion | justification |
| asistencia_dia | attendance_day |
| auditoria | audit_log |

## Entidades y campos clave

### user_account
id PK · username UNIQUE · password_hash · role_name · is_active Y/N

### institution
id PK · ugel · school_name · modular_code · education_level · shift_name · is_active

### staff_member
id PK · dni UNIQUE (8) · last_names · first_names · job_title · employment_status · is_active · registered_at

### staff_institution
id PK · staff_member_id FK · institution_id FK · start_date · end_date · is_active

### biometric_import
id PK · file_name · file_path · uploaded_at · user_account_id FK  
**status** draft|confirmed|cancelled · **period_start** · **period_end**  
total_rows · ok_rows · error_rows · matched_rows · new_rows

### biometric_mark
id PK · staff_member_id FK · biometric_import_id FK · marked_at · mark_type entry|exit · status valid|inconsistent|corrected

### inconsistency
id PK · mark_id FK · issue_type · description · status pending|reviewed|corrected · detected_at

### justification
id PK · staff_member_id FK · start_date · end_date · norm_code · with_pay Y/N · reason · support_file_path · registered_by_id · registered_at · status active|cancelled

### attendance_day
id PK · staff_member_id FK · biometric_import_id FK NULL · attendance_date · status no_record|present|late|absent|justified|leave|unpaid_leave|permission|strike|holiday · late_minutes ≥0 · justification_id FK NULL
UNIQUE (staff_member_id, attendance_date, biometric_import_id)

### audit_log
id PK · user_account_id FK · entity_name · entity_id · action_name · old_value · new_value · created_at

Scripts: `database/01_schema/01_create_tables.sql`
