@echo off
setlocal EnableExtensions

set "BASE_DIR=%~dp0"

set "DB_HOST=localhost"
set "DB_PORT=1521"
set "DB_USER=ASISTENCIA_OWNER"
set "DB_PASSWORD=Asistencia123"
set "PDB_NAME=%~1"

cls

echo ============================================
echo   GENERADOR DE VARIABLES - ASISTENCIA
echo ============================================
echo.

if "%PDB_NAME%"=="" (
    set /p PDB_NAME=Ingrese el nombre de la PDB: 
)

if "%PDB_NAME%"=="" (
    echo.
    echo ERROR: Debe ingresar una PDB.
    goto :ERROR
)

if not exist "%BASE_DIR%backend\" (
    echo.
    echo ERROR: No existe la carpeta backend.
    goto :ERROR
)

if not exist "%BASE_DIR%frontend\" (
    echo.
    echo ERROR: No existe la carpeta frontend.
    goto :ERROR
)

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

(
    echo APP_NAME="CHIQUISTRUKIS API"
    echo APP_ENV="development"
    echo APP_DEBUG="true"
    echo.
    echo ORACLE_USER="%DB_USER%"
    echo ORACLE_PASSWORD="%DB_PASSWORD%"
    echo ORACLE_DSN="%DB_HOST%:%DB_PORT%/%PDB_NAME%"
    echo.
    echo REDIS_URL="redis://127.0.0.1:6379/0"
    echo ACCESS_TOKEN_EXPIRE_MINUTES="60"
    echo APP_ALLOW_MEMORY_SESSION="true"
) > "%BASE_DIR%backend\.env"

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo generar backend\.env.
    goto :ERROR
)

(
    echo VITE_API_BASE_URL="http://127.0.0.1:8000"
) > "%BASE_DIR%frontend\.env"

if errorlevel 1 (
    echo.
    echo ERROR: No se pudo generar frontend\.env.
    goto :ERROR
)

echo [OK] backend\.env generado
echo [OK] frontend\.env generado
echo.
echo Listo. Este script solo genera variables, no instala ni modifica la BD.
echo.

pause
exit /b 0

:ERROR
echo.
echo ============================================
echo GENERACION INTERRUMPIDA
echo ============================================
echo.
echo Revise el error mostrado anteriormente.
echo.
pause
exit /b 1
