SET ECHO OFF
SET VERIFY OFF
SET FEEDBACK ON
SET SERVEROUTPUT ON

WHENEVER SQLERROR EXIT SQL.SQLCODE

PROMPT ============================================
PROMPT [3/5] CREANDO / VALIDANDO INDICES
PROMPT ============================================

DECLARE
    FUNCTION index_exists(p_index_name IN VARCHAR2) RETURN BOOLEAN IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM user_indexes
        WHERE index_name = UPPER(p_index_name);

        RETURN v_count > 0;
    END;

    FUNCTION equivalent_index_exists(
        p_table_name IN VARCHAR2,
        p_column_list IN VARCHAR2
    ) RETURN BOOLEAN IS
        v_count NUMBER;
    BEGIN
        SELECT COUNT(*)
        INTO v_count
        FROM (
            SELECT i.index_name,
                   LISTAGG(c.column_name, ',') WITHIN GROUP (ORDER BY c.column_position) AS columns_key
            FROM user_indexes i
            JOIN user_ind_columns c ON c.index_name = i.index_name
            WHERE i.table_name = UPPER(p_table_name)
            GROUP BY i.index_name
        )
        WHERE columns_key = UPPER(REPLACE(p_column_list, ' ', ''));

        RETURN v_count > 0;
    END;

    PROCEDURE create_index_if_missing(
        p_index_name IN VARCHAR2,
        p_table_name IN VARCHAR2,
        p_column_list IN VARCHAR2,
        p_sql IN VARCHAR2
    ) IS
    BEGIN
        IF index_exists(p_index_name) THEN
            DBMS_OUTPUT.PUT_LINE('[OK] Indice ' || UPPER(p_index_name) || ' ya existe');
        ELSIF equivalent_index_exists(p_table_name, p_column_list) THEN
            DBMS_OUTPUT.PUT_LINE('[OK] Indice equivalente para ' || UPPER(p_table_name) || '(' || p_column_list || ') ya existe');
        ELSE
            EXECUTE IMMEDIATE p_sql;
            DBMS_OUTPUT.PUT_LINE('[CREATE] Indice ' || UPPER(p_index_name) || ' creado');
        END IF;
    END;
BEGIN
    create_index_if_missing('ix_staff_institution_staff', 'staff_institution', 'staff_member_id',
        'CREATE INDEX ix_staff_institution_staff ON staff_institution (staff_member_id)');
    create_index_if_missing('ix_staff_institution_inst', 'staff_institution', 'institution_id',
        'CREATE INDEX ix_staff_institution_inst ON staff_institution (institution_id)');
    create_index_if_missing('ix_biometric_import_status', 'biometric_import', 'status,period_start',
        'CREATE INDEX ix_biometric_import_status ON biometric_import (status, period_start)');
    create_index_if_missing('ix_biometric_mark_import', 'biometric_mark', 'biometric_import_id',
        'CREATE INDEX ix_biometric_mark_import ON biometric_mark (biometric_import_id)');
    create_index_if_missing('ix_biometric_mark_staff', 'biometric_mark', 'staff_member_id,marked_at',
        'CREATE INDEX ix_biometric_mark_staff ON biometric_mark (staff_member_id, marked_at)');
    create_index_if_missing('ix_inconsistency_status', 'inconsistency', 'status',
        'CREATE INDEX ix_inconsistency_status ON inconsistency (status)');
    create_index_if_missing('ix_justification_staff', 'justification', 'staff_member_id,status',
        'CREATE INDEX ix_justification_staff ON justification (staff_member_id, status)');
    create_index_if_missing('ix_attendance_day_date', 'attendance_day', 'attendance_date',
        'CREATE INDEX ix_attendance_day_date ON attendance_day (attendance_date)');
    create_index_if_missing('ix_attendance_day_import', 'attendance_day', 'biometric_import_id,attendance_date',
        'CREATE INDEX ix_attendance_day_import ON attendance_day (biometric_import_id, attendance_date)');
    create_index_if_missing('ix_audit_log_entity', 'audit_log', 'entity_name,entity_id',
        'CREATE INDEX ix_audit_log_entity ON audit_log (entity_name, entity_id)');
END;
/

PROMPT ============================================
PROMPT [OK] INDICES VALIDADOS
PROMPT ============================================

EXIT SUCCESS
