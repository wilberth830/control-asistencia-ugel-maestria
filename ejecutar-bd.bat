@echo off
setlocal EnableExtensions

set "BASE_DIR=%~dp0"

set "DB_HOST=localhost"
set "DB_PORT=1521"
set "DB_USER=ASISTENCIA_OWNER"
set "DB_PASSWORD=Asistencia123"
set "PDB_NAME="

cls

echo ============================================
echo   INSTALADOR BASE DE DATOS - ASISTENCIA
echo ============================================
echo.

if not "%~1"=="" (
    set "PDB_NAME=%~1"
)

if "%PDB_NAME%"=="" (
    set /p PDB_NAME=Ingrese el nombre de la PDB: 
)

if "%PDB_NAME%"=="" (
    echo.
    echo ERROR: Debe ingresar una PDB.
    goto :ERROR
)

where sqlplus >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: sqlplus no esta disponible en PATH.
    goto :ERROR
)

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: python no esta disponible en PATH.
    goto :ERROR
)

call :REQUIRE_FILE "%BASE_DIR%database\00_configuracion\00_create_schema.sql"
if errorlevel 1 goto :ERROR

call :REQUIRE_FILE "%BASE_DIR%database\01_schema\01_create_tables.sql"
if errorlevel 1 goto :ERROR

call :REQUIRE_FILE "%BASE_DIR%database\01_schema\02_create_indexes.sql"
if errorlevel 1 goto :ERROR

call :REQUIRE_FILE "%BASE_DIR%database\02_seed\01_seed_demo.sql"
if errorlevel 1 goto :ERROR

call :REQUIRE_FILE "%BASE_DIR%database\03_checks\check_p1_static.py"
if errorlevel 1 goto :ERROR

call :REQUIRE_FILE "%BASE_DIR%database\03_checks\check_idempotency.py"
if errorlevel 1 goto :ERROR

echo.
echo ============================================
echo CONFIGURACION
echo ============================================
echo Host:      %DB_HOST%
echo Puerto:    %DB_PORT%
echo PDB:       %PDB_NAME%
echo Usuario:   %DB_USER%
echo Password:  ********
echo ============================================
echo.

echo [1/5] Configurando PDB y schema...
echo.

call :RUN_SYSDBA "%BASE_DIR%database\00_configuracion\00_create_schema.sql" "%PDB_NAME%" "%DB_USER%" "%DB_PASSWORD%"

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo configurar el schema.
    goto :ERROR
)

echo.
echo [2/5] Creando/validando tablas...
echo.

call :RUN_OWNER "%BASE_DIR%database\01_schema\01_create_tables.sql"

if errorlevel 1 (
    echo.
    echo ERROR: Fallo la creacion/validacion de tablas.
    goto :ERROR
)

echo.
echo [3/5] Creando/validando indices...
echo.

call :RUN_OWNER "%BASE_DIR%database\01_schema\02_create_indexes.sql"

if errorlevel 1 (
    echo.
    echo ERROR: Fallo la creacion/validacion de indices.
    goto :ERROR
)

echo.
echo [4/5] Ejecutando datos seed...
echo.

call :RUN_OWNER "%BASE_DIR%database\02_seed\01_seed_demo.sql"

if errorlevel 1 (
    echo.
    echo ERROR: Fallo la carga de datos seed.
    goto :ERROR
)

echo.
echo [5/5] Ejecutando checks...
echo.

python "%BASE_DIR%database\03_checks\check_p1_static.py"

if errorlevel 1 (
    echo.
    echo ERROR: Fallaron las validaciones estaticas P1.
    goto :ERROR
)

python "%BASE_DIR%database\03_checks\check_idempotency.py"

if errorlevel 1 (
    echo.
    echo ERROR: Fallaron las validaciones de idempotencia.
    goto :ERROR
)

echo.
echo ============================================
echo INSTALACION COMPLETADA CORRECTAMENTE
echo ============================================
echo.
echo PDB:       %PDB_NAME%
echo Usuario:   %DB_USER%
echo Host:      %DB_HOST%
echo Puerto:    %DB_PORT%
echo.
echo La base de datos esta lista.
echo.

pause
exit /b 0

:REQUIRE_FILE
if not exist "%~1" (
    echo.
    echo ERROR: No existe el archivo:
    echo "%~1"
    exit /b 1
)
exit /b 0

:RUN_SYSDBA
set "TMP_SQL=%TEMP%\asistencia_sys_%RANDOM%_%RANDOM%.sql"

(
    echo SET ECHO OFF
    echo SET VERIFY OFF
    echo SET FEEDBACK ON
    echo WHENEVER SQLERROR EXIT SQL.SQLCODE
    echo CONNECT / AS SYSDBA
    echo @"%~1" "%~2" "%~3" "%~4"
    echo EXIT
) > "%TMP_SQL%"

sqlplus -L -S /nolog @"%TMP_SQL%"
set "SQLPLUS_RC=%ERRORLEVEL%"
del "%TMP_SQL%" >nul 2>nul
exit /b %SQLPLUS_RC%

:RUN_OWNER
set "TMP_SQL=%TEMP%\asistencia_owner_%RANDOM%_%RANDOM%.sql"

(
    echo SET ECHO OFF
    echo SET VERIFY OFF
    echo SET FEEDBACK ON
    echo WHENEVER SQLERROR EXIT SQL.SQLCODE
    echo CONNECT %DB_USER%/%DB_PASSWORD%@%DB_HOST%:%DB_PORT%/%PDB_NAME%
    echo @"%~1"
    echo EXIT
) > "%TMP_SQL%"

sqlplus -L -S /nolog @"%TMP_SQL%"
set "SQLPLUS_RC=%ERRORLEVEL%"
del "%TMP_SQL%" >nul 2>nul
exit /b %SQLPLUS_RC%

:ERROR
echo.
echo ============================================
echo INSTALACION INTERRUMPIDA
echo ============================================
echo.
echo Revise el error mostrado anteriormente.
echo.
pause
exit /b 1
