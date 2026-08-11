-- CHIQUISTRUKIS - Limpieza de datos cargados
-- Borra datos operativos generados por cargas biometricas.
-- No borra schema, usuario demo, institucion demo ni personal seed.

SET ECHO OFF
SET VERIFY OFF
SET FEEDBACK ON
SET SERVEROUTPUT ON

WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

PROMPT ============================================
PROMPT LIMPIEZA DE DATOS CARGADOS
PROMPT ============================================

DECLARE
    v_attendance_deleted       NUMBER := 0;
    v_inconsistency_deleted    NUMBER := 0;
    v_mark_deleted             NUMBER := 0;
    v_import_deleted           NUMBER := 0;
    v_staff_relation_deleted   NUMBER := 0;
    v_staff_deleted            NUMBER := 0;
    v_audit_deleted            NUMBER := 0;
BEGIN
    DELETE FROM audit_log
    WHERE entity_name IN (
        'attendance_day',
        'biometric_import',
        'biometric_mark',
        'inconsistency'
    );
    v_audit_deleted := SQL%ROWCOUNT;

    DELETE FROM attendance_day;
    v_attendance_deleted := SQL%ROWCOUNT;

    DELETE FROM inconsistency
    WHERE mark_id IN (
        SELECT id
        FROM biometric_mark
    );
    v_inconsistency_deleted := SQL%ROWCOUNT;

    DELETE FROM biometric_mark;
    v_mark_deleted := SQL%ROWCOUNT;

    DELETE FROM biometric_import;
    v_import_deleted := SQL%ROWCOUNT;

    DELETE FROM staff_institution
    WHERE staff_member_id IN (
        SELECT id
        FROM staff_member
        WHERE employment_status LIKE 'Registrado en carga biom%'
          AND dni NOT IN ('45678912', '71234567', '40112233')
          AND NOT EXISTS (
              SELECT 1
              FROM justification
              WHERE justification.staff_member_id = staff_member.id
          )
    );
    v_staff_relation_deleted := SQL%ROWCOUNT;

    DELETE FROM staff_member
    WHERE employment_status LIKE 'Registrado en carga biom%'
      AND dni NOT IN ('45678912', '71234567', '40112233')
      AND NOT EXISTS (
          SELECT 1
          FROM justification
          WHERE justification.staff_member_id = staff_member.id
      );
    v_staff_deleted := SQL%ROWCOUNT;

    COMMIT;

    DBMS_OUTPUT.PUT_LINE('[OK] audit_log borrados: ' || v_audit_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] attendance_day borrados: ' || v_attendance_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] inconsistency borrados: ' || v_inconsistency_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] biometric_mark borrados: ' || v_mark_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] biometric_import borrados: ' || v_import_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] staff_institution auto borrados: ' || v_staff_relation_deleted);
    DBMS_OUTPUT.PUT_LINE('[OK] staff_member auto borrados: ' || v_staff_deleted);
END;
/

PROMPT ============================================
PROMPT [OK] LIMPIEZA COMPLETADA
PROMPT ============================================

EXIT SUCCESS
