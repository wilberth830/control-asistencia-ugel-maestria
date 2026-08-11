# Precios IA en carga biometrica

## Cuando ingresa a IA

La IA solo se intenta durante la carga de archivos biometricos cuando el backend
no puede reconocer el formato con el parser normal ni con el detector local de
columnas.

Ejemplo de archivo que ingresa a IA:

```text
C1|C2|C3|C4|C5
88001001|Quispe Huaman|Ana Carmen|2026-08-03 07:47:08|entrada
```

En ese caso, la IA ayuda a descubrir cual columna corresponde a DNI, apellidos,
nombres, fecha/hora y tipo de marca.

## Otros casos donde se usaria IA

Ademas de identificar columnas ambiguas en archivos biometricos, la IA podria
usarse en estos casos:

- Normalizar archivos exportados por distintos relojes biometricos cuando cambian
  nombres de columnas, separadores o estructura.
- Detectar si una columna mezcla fecha y hora en formatos no estandar, por
  ejemplo `03/08/2026 7:47 a. m.` o textos similares.
- Sugerir equivalencias para tipos de marca raros, por ejemplo `ENT`, `ING`,
  `OUT`, `SAL`, `CHECKIN` o `CHECKOUT`.
- Separar nombres completos cuando el archivo solo trae una columna de trabajador
  y no trae apellidos/nombres por separado.
- Sugerir posibles inconsistencias de asistencia, como entrada sin salida, salida
  sin entrada, doble marcacion o marcas fuera del horario esperado.
- Ayudar a interpretar archivos con encabezados poco claros, abreviados o
  generados por un dispositivo biometrico diferente.

La IA no debe confirmar cargas, registrar docentes, modificar asistencia ni
aprobar justificaciones automaticamente. Solo sugiere o normaliza el formato
para que el sistema y el usuario continúen el flujo.

## Cuando no ingresa a IA

No entra a IA cuando el archivo ya trae columnas reconocibles, por ejemplo:

```text
dni,apellidos,nombres,fecha_hora,tipo_marca
```

Tampoco entra si usa alias comunes como:

```text
document, punch_time, direction, timestamp, entrada, salida
```

## Como se calcula el costo

El backend no envia todo el archivo a la IA. Solo envia una muestra de filas y
los nombres de columnas para que la IA devuelva el mapeo. Luego Python procesa
todas las filas localmente.

Por eso el costo depende mas del formato detectado que de la cantidad total de
registros del archivo.

Referencia con `gpt-5.2`:

```text
Input:  $1.75 por 1M tokens
Output: $14.00 por 1M tokens
```

Un token no es lo mismo que una fila. Un token es una parte pequeña de texto:
puede ser una palabra corta, una parte de una palabra, un numero o un simbolo.
Por ejemplo, una fila biometrica como esta:

```text
88001001|Quispe Huaman|Ana Carmen|2026-08-03 07:47:08|entrada
```

puede consumir aproximadamente entre 20 y 35 tokens, dependiendo del formato.
Ademas se suman tokens por instrucciones internas, nombres de columnas y
respuesta de la IA.

Como el sistema envia una muestra y no todo el archivo, el consumo estimado suele
verse asi:

```text
Archivo con 10 filas:    envia aprox. 10 filas a IA
Archivo con 100 filas:   envia aprox. 25 filas a IA
Archivo con 1000 filas:  envia aprox. 25 filas a IA
Archivo con 4400 filas:  envia aprox. 25 filas a IA
```

Por eso, desde 100 filas hacia arriba, el costo no crece proporcionalmente con
la cantidad de datos cargados. La IA solo ayuda a entender el formato; el resto
lo procesa Python.

Estimacion practica:

```text
1 carga con IA real:  $0.001 a $0.004 aprox.
$0.10 de consumo:     25 a 100 cargas con IA real aprox.
```

Ejemplo por cantidad de datos:

```text
10 filas ambiguas:    $0.001 a $0.003 aprox.
100 filas ambiguas:   $0.002 a $0.004 aprox.
1000 filas ambiguas:  $0.002 a $0.004 aprox.
4400 filas ambiguas:  $0.002 a $0.004 aprox.
```

Si en el futuro se cambia para enviar todo el archivo completo a IA, ahi si el
costo creceria por cantidad de filas. Con el flujo actual, el costo crece poco
porque solo se manda la muestra.

## Donde se registra

Cuando se usa IA real, el nombre final del archivo incluye:

```text
ia_usd_<costo>
```

Ademas se registra el consumo en la tabla `ai_usage_log` con:

```text
biometric_import_id
file_name
provider
model_name
input_tokens
output_tokens
total_tokens
estimated_cost_usd
created_at
```

Si se resuelve por parser normal o fallback local, el costo es `0` y no se
registra consumo de IA.
