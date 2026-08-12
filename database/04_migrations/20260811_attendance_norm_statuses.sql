-- Amplía los estados diarios según la R.S.G. N.° 326-2017-MINEDU.
-- Ejecutar una vez en instalaciones existentes.

SET SERVEROUTPUT ON;
WHENEVER SQLERROR EXIT SQL.SQLCODE;

DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count
      FROM user_constraints
     WHERE constraint_name = 'CK_AD_STATUS';

    IF v_count > 0 THEN
        EXECUTE IMMEDIATE
            'ALTER TABLE attendance_day DROP CONSTRAINT ck_ad_status';
    END IF;

    EXECUTE IMMEDIATE q'[
        ALTER TABLE attendance_day ADD CONSTRAINT ck_ad_status
        CHECK (status IN (
            'no_record', 'present', 'late', 'absent', 'justified', 'leave',
            'unpaid_leave', 'permission', 'strike', 'holiday'
        ))
    ]';
END;
/

COMMIT;
PROMPT Estados normativos de attendance_day actualizados correctamente.
