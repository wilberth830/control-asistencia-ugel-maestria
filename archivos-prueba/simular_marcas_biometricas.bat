@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  Ejemplo: simulación de marcas de un dispositivo biométrico
::  Genera un CSV similar al export de un reloj de asistencia
::  (solo DEMO académico — no conecta a hardware real)
:: ============================================================

set "OUTDIR=%~dp0salida"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"

:: Nombre de archivo con fecha/hora
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do (
  set "DD=%%a"
  set "MM=%%b"
  set "YYYY=%%c"
)
set "STAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "STAMP=%STAMP: =0%"
set "OUTFILE=%OUTDIR%\marcas_biometricas_%STAMP%.csv"

echo.
echo  ========================================
echo   SIMULADOR DE RELOJ BIOMETRICO (DEMO)
echo  ========================================
echo.
echo  Este script NO habla con un dispositivo real.
echo  Solo genera un CSV de ejemplo como el que
echo  exportan muchos relojes (DNI, fecha_hora, tipo).
echo.

:: Cabecera compatible con carga CHIQUISTRUKIS (ejemplo)
> "%OUTFILE%" echo dni,apellidos,nombres,fecha_hora,tipo_marca

:: --- Personal de ejemplo (DNI 8 digitos) ---
:: Formato fecha_hora: YYYY-MM-DD HH:MM:SS  |  tipo: entrada / salida

:: Docente 1 - dia laborable tipico
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-16 07:55:12,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-16 13:02:41,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-17 08:01:05,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-17 13:00:18,salida

:: Docente 2 - con una tardanza
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-06-16 08:22:33,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-06-16 13:05:02,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-06-17 07:58:44,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-06-17 13:01:10,salida

:: Auxiliar
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-06-16 07:45:01,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-06-16 14:00:55,salida

:: Marca "nueva" (DNI no existente en personal) — para probar fila ROJA del wizard
>> "%OUTFILE%" echo 99998888,Perez Soto,Juan Carlos,2026-06-16 08:10:00,entrada
>> "%OUTFILE%" echo 99998888,Perez Soto,Juan Carlos,2026-06-16 13:00:00,salida

>> "%OUTFILE%" echo 99000001,Perez Soto,Juan Carlos,2026-06-16 08:10:00,entrada
>> "%OUTFILE%" echo 99000001,Perez Soto,Juan Carlos,2026-06-16 13:00:00,salida

>> "%OUTFILE%" echo 99000002,Perez Soto,Juan Carlos,2026-06-16 08:10:00,entrada
>> "%OUTFILE%" echo 99000002,Perez Soto,Juan Carlos,2026-06-16 13:00:00,salida

>> "%OUTFILE%" echo 99000003,Perez Soto,Juan Carlos,2026-06-16 08:10:00,entrada
:: Duplicado intencional — para probar inconsistencias
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-06-16 07:55:12,entrada

echo  Archivo generado:
echo  %OUTFILE%
echo.
echo  Columnas: dni, apellidos, nombres, fecha_hora, tipo_marca
echo  Filas de ejemplo: asistencias, tardanza, personal nuevo, duplicado.
echo.
echo  En el sistema CHIQUISTRUKIS:
echo   1. Modulo Asistencia biometrica
echo   2. Subir este CSV
echo   3. Wizard: verde = encontrado / rojo = nuevo
echo   4. Finalizar -^> consolida attendance_day
echo.
pause
endlocal
