
# Almacenamiento y Procesamiento de Grandes Datos

Repositorio de laboratorios de la asignatura Almacenamiento y Procesamiento de Grandes Datos, Universidad EAFIT.

## Laboratorios

### Laboratorio 1 - Modelado OLTP a OLAP

Implementacion de un esquema estrella para PayTrack Colombia mediante PostgreSQL.

Incluye:
- Modelado dimensional y SCD Tipo 2.
- Proceso ELT de carga de dimensiones y hechos.
- Tres consultas analiticas equivalentes al OLTP.
- Comparacion de rendimiento mediante EXPLAIN ANALYZE.
- Experimentos con indices.
- Informe final, diagrama y evidencias de validacion.

[Ver Laboratorio 1](labs/01-modelado/)

## Laboratorio 2 - Lakehouse Batch y Streaming

Implementacion de un lakehouse para PayTrack utilizando
AWS S3, Glue, Delta Lake, Athena, Kinesis y Apache Kafka.

Se desarrollaron pipelines Batch y Streaming con
arquitectura Medallion, controles de calidad, auditoria,
deduplicacion y deteccion de posibles fraudes.

**[Ver la entrega completa del Laboratorio 2](labs/02-lakehouse/ENTREGA.md)**
## Referencia

Material base del curso: [big-data-labs-2026-2](https://github.com/asacrea/big-data-labs-2026-2), proporcionado por Andres Sacre Alzate.

