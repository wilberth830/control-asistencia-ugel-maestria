@echo off
setlocal

set "OUTFILE=%~dp0marcas_julio_2026_mes_completo.csv"

echo Generando archivo biometrico mensual...
echo Destino: %OUTFILE%

> "%OUTFILE%" echo dni,apellidos,nombres,fecha_hora,tipo_marca
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-01 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-01 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-01 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-01 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-01 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-01 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-02 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-02 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-02 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-02 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-02 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-02 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-03 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-03 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-03 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-03 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-03 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-03 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-06 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-06 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-06 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-06 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-06 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-06 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-07 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-07 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-07 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-07 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-07 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-07 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-08 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-08 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-08 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-08 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-08 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-08 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-09 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-09 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-09 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-09 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-09 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-09 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-10 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-10 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-10 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-10 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-10 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-10 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-13 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-13 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-13 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-13 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-13 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-13 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-14 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-14 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-14 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-14 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-14 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-14 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-15 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-15 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-15 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-15 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-15 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-15 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-16 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-16 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-16 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-16 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-16 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-16 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-17 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-17 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-17 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-17 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-17 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-17 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-20 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-20 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-20 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-20 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-20 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-20 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-21 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-21 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-21 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-21 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-21 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-21 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-22 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-22 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-22 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-22 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-22 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-22 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-23 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-23 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-23 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-23 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-23 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-23 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-24 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-24 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-24 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-24 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-24 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-24 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-27 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-27 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-27 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-27 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-27 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-27 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-28 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-28 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-28 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-28 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-28 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-28 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-29 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-29 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-29 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-29 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-29 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-29 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-30 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-30 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-30 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-30 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-30 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-30 14:00:40,salida
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-31 07:52:10,entrada
>> "%OUTFILE%" echo 45678912,Quispe Mamani,Maria Elena,2026-07-31 13:01:20,salida
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-31 08:04:15,entrada
>> "%OUTFILE%" echo 71234567,Huaman Rojas,Carlos Alberto,2026-07-31 13:03:30,salida
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-31 07:46:05,entrada
>> "%OUTFILE%" echo 40112233,Flores Ilacopa,Leida Idalecia,2026-07-31 14:00:40,salida

echo.
echo Archivo generado correctamente.
echo Filas de marcas: 138
echo Periodo: 2026-07-01 al 2026-07-31
echo Tambien puedes subir este .bat directamente al sistema.
echo.

endlocal
