SET ECHO OFF
SET VERIFY OFF
SET FEEDBACK ON
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

DEFINE PDB_NAME = '&1'
DEFINE APP_USER = '&2'
DEFINE APP_PASSWORD = '&3'

PROMPT ============================================
PROMPT [1/5] CONFIGURANDO PDB Y SCHEMA
PROMPT PDB: &&PDB_NAME
PROMPT Usuario aplicacion: &&APP_USER
PROMPT ============================================

ALTER SESSION SET CONTAINER = &&PDB_NAME;

DECLARE
    v_user          VARCHAR2(128) := UPPER('&&APP_USER');
    v_password      VARCHAR2(256) := '&&APP_PASSWORD';
    v_default_ts    VARCHAR2(128);
    v_temp_ts       VARCHAR2(128);
    v_count         NUMBER;
BEGIN
    BEGIN
        SELECT tablespace_name
          INTO v_default_ts
          FROM (
                SELECT tablespace_name,
                       CASE WHEN tablespace_name = 'USERS' THEN 0 ELSE 1 END AS prioridad
                  FROM dba_tablespaces
                 WHERE contents = 'PERMANENT'
                   AND status = 'ONLINE'
                   AND tablespace_name NOT IN ('SYSTEM', 'SYSAUX')
                 ORDER BY prioridad, tablespace_name
               )
         WHERE ROWNUM = 1;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            SELECT property_value
              INTO v_default_ts
              FROM database_properties
             WHERE property_name = 'DEFAULT_PERMANENT_TABLESPACE';

            DBMS_OUTPUT.PUT_LINE(
                '[WARN] La PDB no tiene un tablespace de aplicacion dedicado.'
            );
            DBMS_OUTPUT.PUT_LINE(
                '[WARN] Se utilizara el tablespace por defecto: ' || v_default_ts
            );
    END;

    SELECT property_value
      INTO v_temp_ts
      FROM database_properties
     WHERE property_name = 'DEFAULT_TEMP_TABLESPACE';

    DBMS_OUTPUT.PUT_LINE('[INFO] Tablespace permanente: ' || v_default_ts);
    DBMS_OUTPUT.PUT_LINE('[INFO] Tablespace temporal:   ' || v_temp_ts);

    SELECT COUNT(*)
      INTO v_count
      FROM dba_users
     WHERE username = v_user;

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE
            'CREATE USER ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_user) ||
            ' IDENTIFIED BY "' || REPLACE(v_password, '"', '""') || '"' ||
            ' DEFAULT TABLESPACE ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_default_ts) ||
            ' TEMPORARY TABLESPACE ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_temp_ts);

        DBMS_OUTPUT.PUT_LINE('[CREATE] Usuario ' || v_user || ' creado.');
    ELSE
        EXECUTE IMMEDIATE
            'ALTER USER ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_user) ||
            ' IDENTIFIED BY "' || REPLACE(v_password, '"', '""') || '"' ||
            ' DEFAULT TABLESPACE ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_default_ts) ||
            ' TEMPORARY TABLESPACE ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_temp_ts) ||
            ' ACCOUNT UNLOCK';

        DBMS_OUTPUT.PUT_LINE('[OK] Usuario ' || v_user || ' ya existe.');
    END IF;

    EXECUTE IMMEDIATE
        'ALTER USER ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_user) ||
        ' QUOTA UNLIMITED ON ' || DBMS_ASSERT.SIMPLE_SQL_NAME(v_default_ts);

    DBMS_OUTPUT.PUT_LINE(
        '[OK] Quota configurada sobre ' || v_default_ts || '.'
    );
END;
/

GRANT CREATE SESSION TO &&APP_USER;
GRANT CREATE TABLE TO &&APP_USER;
GRANT CREATE VIEW TO &&APP_USER;
GRANT CREATE SEQUENCE TO &&APP_USER;
GRANT CREATE PROCEDURE TO &&APP_USER;
GRANT CREATE TRIGGER TO &&APP_USER;

PROMPT ============================================
PROMPT SCHEMA CONFIGURADO CORRECTAMENTE
PROMPT ============================================

EXIT SUCCESS
