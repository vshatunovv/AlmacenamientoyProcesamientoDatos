# Laboratorio 02 - PayTrack Lakehouse: Batch y Streaming

**Asignatura:** Almacenamiento y Procesamiento de Grandes Datos - Universidad EAFIT  
**Integrantes:** Vladlen Shatunov y Juan Alberto Rodriguez  
**Fecha de entrega:** 6 de noviembre de 2026

## Objetivo

Implementar un lakehouse de PayTrack con procesamiento por lotes y en tiempo real, usando S3, Delta Lake, AWS Glue, Athena, Kinesis y, en local, Kafka. La arquitectura Medallion separa Bronze, Silver y Gold, integra los pagos en una misma tabla Silver y proporciona controles de calidad, auditoría, métricas y alertas de fraude.

## Archivos principales

| Componente | Ubicación |
| --- | --- |
| Ingesta de lotes | [`ingest.py`](ingest.py) |
| Productor de eventos | [`producer.py`](producer.py) |
| Jobs Bronze, Silver, Gold, Audit y Streaming | [`jobs/`](jobs/) |
| Consultas para Athena | [`sql/athena.sql`](sql/athena.sql) |
| Infraestructura AWS | [`infra/serverless.yml`](infra/serverless.yml) |
| Pruebas automatizadas | [`tests/`](tests/) |
| Ejecución local y AWS | [`run_local.sh`](run_local.sh), [`run_aws.sh`](run_aws.sh) |
| Informe final | [`docs/Informe_Lab02.pdf`](docs/Informe_Lab02.pdf) |
| Diagrama editable | [`docs/Arquitectura_Lab02.drawio`](docs/Arquitectura_Lab02.drawio) |
| Enunciado del laboratorio | [`README.md`](README.md) |

## Resultados de validación

Las ejecuciones se realizaron con datos sintéticos de PayTrack. Los archivos de `evidencias/` son salidas reales de las ejecuciones y no contienen tablas Delta locales completas.

### Pruebas y procesamiento Batch local

- `pytest`: **15/15 pruebas aprobadas**. [Registro](evidencias/Local/pytest.txt).
- Batch 1 (`2026-09-29`): **30.600** filas raw de transacciones, **28.230** transacciones válidas insertadas y **1.770** registros únicos en cuarentena. [Registro](evidencias/Local/Batch1_Local.txt).
- Batch 2 (`2026-09-30`): **2.316** filas raw; **1.883** inserciones, **275** cambios a `chargeback` y **118** registros únicos en cuarentena. La auditoría detectó un monto revertido de **19.660.867,66 COP**. [Registro](evidencias/Local/Batch2_Local.txt).
- Reejecución del Batch 2: **0 inserciones y 0 actualizaciones lógicas**, validaciones correctas; Delta creó la versión 3 y reportó filas copiadas físicamente. [Registro](evidencias/Local/Batch2_Idempotencia.txt).
- Cuarentena por motivo: lote 1, **1.176** `invalid_amount` y **594** `missing_customer`; lote 2, **78** `invalid_amount` y **40** `missing_customer`; `invalid_status` **0** en ambos. [CSV](evidencias/Local/Cuarentena_motivos.csv).

### Streaming local

- Reejecución en modo `availableNow` sin nuevos eventos: **0 filas leídas** en las cuatro consultas y todas las validaciones correctas. [Registro](evidencias/Local/Streaming_Idempotencia_1.txt).
- Ejecución en vivo: productor de Kafka con **2.464 eventos enviados en 120 s** (2.412 pagos, 52 contracargos, 0 pérdidas reportadas). Spark procesó **2.464 filas** en cada consulta Bronze, Silver, Metrics y Alerts. Las dos consultas con watermark reportaron **51 descartes cada una**; Silver reportó **0**. Proceso terminado con código de salida **0**. [Productor](evidencias/Local/Streaming_Productor_Live.txt) y [Spark](evidencias/Local/Streaming_Live_Con_Eventos.txt).
- Experimentos de llaves de Kafka: llave constante, **1.238** eventos en una única partición; `transaction_id`, reparto **392 / 411 / 416** entre tres particiones. [Llave constante](evidencias/Local/Kafka_paytrack.experimento.txt) y [transaction_id](evidencias/Local/Kafka_paytrack.experimento-txn.txt).

Los acumulados del Lakehouse local incluyen pruebas anteriores y no deben atribuirse únicamente a la última ejecución en vivo.

### AWS Glue, Athena y experimentos

- Ejecuciones de Glue Batch y Streaming: [índice de ejecuciones](evidencias/AWS/CloudWatch/Indice_Ejecuciones.csv) y [registros de CloudWatch](evidencias/AWS/CloudWatch/).
- Delta Silver en AWS: [historial de versiones y métricas MERGE](evidencias/Delta/Historial_Silver_AWS.csv).
- Comparación de consultas Athena: TODO 1 (Gold) **3,31 KB** escaneados, frente a TODO 2 (Silver) **99,68 KB**; el resultado preagregado redujo los bytes escaneados aproximadamente un **96,68 %**.
- Contracargos: **275**, por **19.660.867,66 COP**.
- Alertas AWS: prueba a tasa configurada de 20/s, **16/17 = 94,12 %** de precisión; a 50/s, **40/60 = 66,67 %**. Las condiciones de las pruebas no fueron idénticas: la diferencia no puede atribuirse solo a la tasa.
- Capturas de las consultas: [carpeta Athena](evidencias/AWS/Athena/). Las métricas y el análisis completo se encuentran en el informe PDF.

## Reproducción local

Desde la raíz del repositorio (requiere `uv`, Docker y dependencias del proyecto):

```bash
uv sync --extra dev
uv run pytest labs/02-lakehouse/tests/test_ingest.py labs/02-lakehouse/tests/test_producer.py -v
uv run python labs/shared/generate_data.py --start-date 2026-08-01 --days 60 --transactions 30000 --dirty-rate 0.02 --output data/batch1
uv run python labs/shared/generate_data.py --start-date 2026-09-30 --days 1 --transactions 2000 --dirty-rate 0.02 --from-batch data/batch1 --id-prefix B2 --output data/batch2
bash labs/02-lakehouse/run_local.sh data/batch1 2026-09-29
bash labs/02-lakehouse/run_local.sh data/batch2 2026-09-30
bash labs/02-lakehouse/run_local.sh data/batch2 2026-09-30
docker compose -f .docker/docker-compose.yml up -d kafka
uv run python labs/02-lakehouse/producer.py --sink kafka --rate 20 --duration 600 --fast
bash labs/02-lakehouse/run_local.sh stream
bash labs/02-lakehouse/run_local.sh stream
```

**Notas:** ejecutar desde un entorno nuevo para reproducir desde cero. No es necesario subir `data/`, `lakehouse-local/`, checkpoints ni credenciales de AWS. Para el modo en vivo se necesitan dos terminales, tal como describe el [`README.md`](README.md) original. En Windows, si Python no lee los JSON en UTF-8, ejecutar con `PYTHONUTF8=1` o `python -X utf8`.

## Observaciones y límites de las evidencias

- Las evidencias anexas corresponden a ejecuciones efectuadas localmente y en AWS; no representan una nueva medición sobre una infraestructura actualmente desplegada.
- No se conserva en este conjunto un registro de la **primera** ejecución `availableNow` con eventos nuevos ni la **segunda ejecución del Batch 1**. Sí están la reejecución `availableNow` a cero filas y la idempotencia completa del Batch 2. Se identifican explícitamente para no confundir evidencias.
- La latencia exacta de emisión de una alerta no se midió con cronómetro externo: el informe distingue comportamiento de watermark y estimaciones de mediciones directas.
- La arquitectura AWS fue desmontada después de las pruebas; se verificó la eliminación de CloudFormation, Kinesis y los datos almacenados en S3. Los registros exportados de CloudWatch se conservaron como evidencia.

## Seguridad y datos

Los lotes son sintéticos. No se incluyen archivos `.env`, credenciales, tablas Delta locales, directorios de Docker o artefactos temporales de ejecución. Los CSV incluidos corresponden exclusivamente a métricas y evidencias del laboratorio.
