# LedgerLens: guía para demostrar y aprender

## Explicación en 45 segundos

“Desarrollé LedgerLens para comparar un registro interno con un proveedor de pagos. Cada fila termina en una coincidencia o una excepción explicada. Uso centavos enteros para evitar errores de precisión y envío referencias duplicadas a revisión, en lugar de elegir una coincidencia arbitraria. Conservo hashes de los archivos, parámetros y evidencia en SQLite. Las decisiones humanas se agregan como eventos y no cambian los resultados originales. Lo validé con datos sintéticos y pruebas de conservación de filas, precisión y repetibilidad.”

No presentes esto como experiencia bancaria ni como un sistema usado por clientes.

## Demostración de cinco minutos

1. Ejecuta `python -m ledgerlens demo --output outputs/demo`.
2. Abre los archivos de entrada y muestra PAY-004: 50.00 contra 48.00.
3. Abre `findings.csv`: explica el delta de -200 centavos.
4. Muestra PAY-008: dos registros internos y uno externo. Todos van a revisión.
5. Ejecuta otra vez el comando: el run ID es igual y no se duplica el historial.
6. Ejecuta las pruebas y explica la conservación de filas.
7. Si instalaste Streamlit, filtra excepciones y agrega una decisión humana.

## Preguntas que debes poder responder

- ¿Por qué no usar float? Los importes decimales pueden introducir errores binarios; los centavos enteros permiten comparación exacta dentro del contrato.
- ¿Por qué no usar matching difuso? Una referencia parecida no demuestra que dos movimientos financieros sean el mismo.
- ¿Una diferencia de 2 dólares significa comisión? No: puede ser comisión, error u otra causa. Se necesita evidencia.
- ¿Qué significa idempotente aquí? Los mismos bytes, versión y parámetros generan un único run en esa base de datos. Un cambio en el orden del CSV cambia el hash.
- ¿Es un historial inviolable? No. Es historial de aplicación; alguien con acceso de escritura a SQLite puede alterarlo.
- ¿Qué cambiarías para producción? Contratos por proveedor, autenticación, secretos, almacenamiento controlado, monitoreo, pruebas con datos reales autorizados y procesamiento de volumen. Primero mediría requisitos y carga.

## Plan de aprendizaje

| Sesión | Objetivo | Práctica |
|---|---|---|
| 1 | Entender el problema | Clasifica manualmente cada movimiento de la demo. |
| 2 | Leer y validar CSV | Agrega una fecha imposible y observa la cuarentena. |
| 3 | Entender el matching | Cambia una referencia y predice el resultado. |
| 4 | Investigar con SQL | Ejecuta `queries.sql` y explica tres excepciones. |
| 5 | Entender las pruebas | Rompe intencionalmente la comparación monetaria y observa el fallo. |
| 6 | Defender decisiones | Explica límites, idempotencia y revisión humana en inglés. |

## Mejoras que puedes implementar personalmente

1. Adaptador a un segundo formato de proveedor, manteniendo el contrato interno.
2. Dataset grande reproducible y benchmark de tiempo y memoria, sin inventar resultados.
3. Regla explícita de comisiones con casos esperados, sin tolerancias silenciosas.
4. Documento de resolución de un caso: hipótesis, consulta, evidencia y conclusión.

## Frase para el CV después de comprender y ejecutar el proyecto

“Built a Python/SQL payment-reconciliation prototype with integer-cent comparisons, duplicate quarantine, row-level evidence, idempotent SQLite audit runs and 11 automated tests; validated on synthetic data.”

La credibilidad viene de explicar el código, reproducir los resultados y reconocer los límites.
