Ejemplo académico — simulación de export de reloj biométrico
============================================================

simular_marcas_biometricas.bat
  Ejecutar en Windows (doble clic o cmd).
  Crea carpeta "salida\" y un CSV con marcas de ejemplo.

marcas_ejemplo_junio.csv
  Mismo contenido, listo para subir sin ejecutar el .bat.

Columnas:
  dni, apellidos, nombres, fecha_hora, tipo_marca

tipo_marca: entrada | salida
fecha_hora: YYYY-MM-DD HH:MM:SS

Incluye:
  - Personal conocido (filas verdes en el wizard)
  - DNI 99998888 nuevo (fila roja)
  - Una marca duplicada (inconsistencia)

NO conecta a hardware real. Solo genera archivo de prueba.
