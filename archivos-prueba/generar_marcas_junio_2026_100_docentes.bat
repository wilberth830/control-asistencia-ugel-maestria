@echo off
setlocal

set "OUTFILE=%~dp0marcas_junio_2026_100_docentes.csv"

echo Generando archivo biometrico mensual de junio 2026...
echo Docentes: 100
echo Destino: %OUTFILE%

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$outFile = $env:OUTFILE; " ^
  "$start = Get-Date '2026-06-01'; " ^
  "$end = Get-Date '2026-06-30'; " ^
  "$firstNames = @('Ana','Luis','Maria','Carlos','Rosa','Jorge','Elena','Miguel','Lucia','Pedro','Carmen','Jose','Teresa','Raul','Patricia','Hugo','Diana','Mario','Sofia','Victor'); " ^
  "$lastA = @('Quispe','Huaman','Flores','Mamani','Condori','Rojas','Vargas','Torres','Salas','Paredes','Chavez','Ramos','Gutierrez','Castillo','Medina','Aguilar','Cruz','Mendoza','Poma','Vega'); " ^
  "$lastB = @('Mamani','Rojas','Ilacopa','Soto','Vega','Poma','Quispe','Huaman','Flores','Torres','Salas','Paredes','Chavez','Ramos','Gutierrez','Castillo','Medina','Aguilar','Cruz','Mendoza'); " ^
  "$rows = New-Object System.Collections.Generic.List[string]; " ^
  "$rows.Add('dni,apellidos,nombres,fecha_hora,tipo_marca'); " ^
  "for ($i = 1; $i -le 100; $i++) { " ^
  "  $dni = '{0:00000000}' -f (88000000 + $i); " ^
  "  $lastNames = $lastA[($i - 1) %% $lastA.Count] + ' ' + $lastB[($i + 6) %% $lastB.Count]; " ^
  "  $firstName = $firstNames[($i - 1) %% $firstNames.Count]; " ^
  "  $secondName = $firstNames[($i + 9) %% $firstNames.Count]; " ^
  "  for ($day = $start; $day -le $end; $day = $day.AddDays(1)) { " ^
  "    if ($day.DayOfWeek -eq 'Saturday' -or $day.DayOfWeek -eq 'Sunday') { continue } " ^
  "    $entryMinute = 45 + (($i + $day.Day) %% 15); " ^
  "    $exitMinute = (($i + ($day.Day * 2)) %% 10); " ^
  "    $entryTime = ('{0:yyyy-MM-dd} 07:{1:00}:{2:00}' -f $day, $entryMinute, (($i * 7 + $day.Day) %% 60)); " ^
  "    $exitTime = ('{0:yyyy-MM-dd} 13:{1:00}:{2:00}' -f $day, $exitMinute, (($i * 11 + $day.Day) %% 60)); " ^
  "    $rows.Add($dni + ',' + $lastNames + ',' + $firstName + ' ' + $secondName + ',' + $entryTime + ',entrada'); " ^
  "    $rows.Add($dni + ',' + $lastNames + ',' + $firstName + ' ' + $secondName + ',' + $exitTime + ',salida'); " ^
  "  } " ^
  "} " ^
  "[System.IO.File]::WriteAllLines($outFile, $rows, [System.Text.UTF8Encoding]::new($false)); " ^
  "Write-Host ('Filas de marcas: ' + ($rows.Count - 1)); " ^
  "Write-Host ('Archivo generado: ' + $outFile);"

if errorlevel 1 (
  echo.
  echo ERROR: No se pudo generar el archivo.
  exit /b 1
)

echo.
echo Archivo generado correctamente.
echo Periodo: 2026-06-01 al 2026-06-30
echo Docentes: 100
echo El CSV generado puede subirse al sistema CHIQUISTRUKIS.
echo.

endlocal
