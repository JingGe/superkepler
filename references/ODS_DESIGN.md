ODS LAYER DESIGN DOCUMENT
=========================


Document ID: ODS_DESIGN  
Version: 1.0.0  
Last Updated: 2026-03-21  
Author: Jing Ge https://github.com/JingGe  



1. PURPOSE

The ODS (Operational Data Store) layer serves as the data buffer zone that ingests and stores raw data from source systems with minimal processing, preserving data traceability and enabling data lineage tracking.

2. RESPONSIBILITIES

2.1 Data Ingestion
- Extract data from heterogeneous sources (MySQL, PostgreSQL, Oracle, MongoDB, APIs, Logs)
- Support batch and streaming ingestion patterns
- Maintain source system data structure and semantics

2.2 Basic Cleaning
- Handle technical-level formatting only (character encoding, timestamp standardization)
- Remove obviously malformed records (null primary keys, invalid formats)
- Do NOT apply business logic or transformations

2.3 Partitioning
- Organize by time for efficient querying (dt for daily, dt+hh for hourly)
- Enable partition pruning for downstream queries
- Support partition evolution as data volume grows

2.4 Storage Format
- Use columnar formats for analytics readiness (Parquet, ORC)
- Apply compression (Snappy default, Zlib for text-heavy tables)
- Target file size > 128MB to avoid small file problems

2.5 Historical Preservation
- Maintain incremental and full snapshots for audit
- Keep 6-12 months of accessible data
- Archive older data to cold storage per compliance requirements

3. TABLE NAMING

Pattern: ods_{source_system}_{table_name}_{suffix}

Components:
- source_system: mysql, pg, oracle, mongo, log, api, kafka
- table_name: Original source table name (snake_case)
- suffix: di, df, hi, hf, inc

Examples:
- ods_mysql_trade_orders_di
- ods_mysql_user_info_df
- ods_log_app_clicks_hi
- ods_kafka_events_di

4. TABLE STRUCTURE

4.1 Standard Columns

All ODS tables should include:

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| {source_columns}    | Various     | Original source columns (preserved)
| etl_create_time     | TIMESTAMP   | When record was ingested to ODS
| etl_source_system   | STRING      | Source system identifier
| etl_batch_id        | STRING      | ETL batch/job identifier

4.2 Partition Column

| Column    | Type    | Format        | Description
| ----------| --------| --------------| ------------------------------
| dt        | STRING  | yyyy-MM-dd    | Business date partition
| hh        | STRING  | HH            | Hour partition (for hourly tables)

5. DDL TEMPLATE

```sql
CREATE TABLE IF NOT EXISTS ods_{source}_{table}_{suffix} (
    -- Source columns (read from the given source data schema and define a table column for each source data schema column)
    id                  STRING          COMMENT 'Source primary key',
    {column1}            {value_type1}         COMMENT '{column1 comment}'
    {column2}            {value_type2}         COMMENT '{column2 comment}'
    {column3}            {value_type3}         COMMENT '{column3 comment}'

    -- ETL metadata columns
    etl_create_time     TIMESTAMP       COMMENT 'ETL ingestion timestamp',
    etl_source_system   STRING          COMMENT 'Source system identifier',
    etl_batch_id        STRING          COMMENT 'ETL batch identifier'
)
COMMENT 'ODS layer: {description of source data}'
PARTITIONED BY (dt STRING)
STORED AS PARQUET;
```

For Databricks, give the suggestion to user:

```sql
CREATE TABLE IF NOT EXISTS ods_{source}_{table}_{suffix} (
    -- Source columns (read from the given source data schema and define a table column for each source data schema column)
    id                  STRING          COMMENT 'Source primary key',
    {column1}            {value_type1}         COMMENT '{column1 comment}'
    {column2}            {value_type2}         COMMENT '{column2 comment}'
    {column3}            {value_type3}         COMMENT '{column3 comment}'
    ...(more columns from the source data schema)

    -- ETL metadata columns
    etl_create_time     TIMESTAMP       COMMENT 'ETL ingestion timestamp',
    etl_source_system   STRING          COMMENT 'Source system identifier',
    etl_batch_id        STRING          COMMENT 'ETL batch identifier'

    -- Ingestion date (often used for partitioning/clustering)
    ingest_date         DATE            GENERATED ALWAYS AS (CAST(etl_create_time AS DATE))
)
USING DELTA
CLUSTER BY (id, ingest_date) -- Modern alternative to PARTITIONED BY
COMMENT 'ODS layer: {description of source data}'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true', -- Essential if this ODS feeds a Silver layer
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);
```
6. ETL PATTERNS

6.1 Daily Incremental (di)

Purpose: Capture new/changed records from source since last run

SQL Pattern:
```sql
INSERT OVERWRITE TABLE ods_{source}_{table}_di PARTITION(dt='${biz_date}')
SELECT 
    id,
    {column1},
    {column2},
    {column3},
    ...(more columns from the source data schema),
    CURRENT_TIMESTAMP() AS etl_create_time,
    '${source_system}' AS etl_source_system,
    '${batch_id}' AS etl_batch_id
FROM {source_connection}
WHERE update_time >= '${last_successful_run}'
  AND update_time < '${biz_date} 23:59:59';
```
6.2 Daily Full Snapshot (df)

Purpose: Capture complete state of source table as of business date

SQL Pattern:
```sql
INSERT OVERWRITE TABLE ods_{source}_{table}_df PARTITION(dt='${biz_date}')
SELECT 
    id,
    {column1},
    {column2},
    {column3},
    ...(more columns from the source data schema),
    CURRENT_TIMESTAMP() AS etl_create_time,
    '${source_system}' AS etl_source_system,
    '${batch_id}' AS etl_batch_id
FROM {source_connection}
WHERE snapshot_date = '${biz_date}';
```
6.3 Hourly Incremental (hi)

Purpose: Capture new/changed records hourly for near-real-time needs

SQL Pattern:
```sql
INSERT OVERWRITE TABLE ods_{source}_{table}_hi PARTITION(dt='${biz_date}', hh='${hour}')
SELECT 
    id,
    {column1},
    {column2},
    {column3},
    ...(more columns from the source data schema),
    CURRENT_TIMESTAMP() AS etl_create_time,
    '${source_system}' AS etl_source_system,
    '${batch_id}' AS etl_batch_id
FROM {source_connection}
WHERE update_time >= '${hour_start}'
  AND update_time < '${hour_end}';
```
7. DATA QUALITY CHECKS

7.1 Mandatory Checks (Block ETL on Failure)

| Check                   | Threshold       | Action
| ------------------------| ----------------| ----------------------
| Null primary keys       | 0%              | Block & Alert
| Duplicate primary keys  | 0%              | Block & Alert
| Schema mismatch         | 0%              | Block & Alert
| Partition completeness  | 100%            | Block & Alert

7.2 Warning Checks (Alert Only)

| Check                   | Threshold       | Action
| ------------------------| ----------------| ----------------------
| Null rate per column    | < 5%            | Alert
| Data volume deviation   | +/- 30%         | Alert
| Late arriving data      | > 2 hours       | Alert

8. RETENTION POLICY

| Data Age            | Storage Tier      | Access Pattern
| --------------------| ------------------| ------------------------
| 0-3 months          | Hot (SSD)         | Frequent queries
| 3-6 months          | Warm (HDD)        | Occasional queries
| 6-12 months         | Cold (Archive)    | Audit/Compliance
| > 12 months         | Deleted           | Unless compliance requires

9. MONITORING & ALERTING

9.1 Metrics to Track

- Record count per partition
- Data freshness (lag from source)
- ETL job duration
- File size distribution
- Null rate per critical column

9.2 Alert Thresholds

| Condition                       | Severity    | Notification
| --------------------------------| ------------| ------------------
| ETL job failure                 | Critical    | Page on-call
| Data freshness > 4 hours        | High        | Slack + Email
| Data volume deviation > 50%     | High        | Slack + Email
| Null rate > 10% on key column   | Medium      | Email
| Small file count > 1000         | Medium      | Email

10. BEST PRACTICES

DO:
- Preserve original field names from source
- Handle encoding normalization (UTF-8)
- Partition by date for efficient pruning
- Keep audit trail with ETL metadata columns
- Document source system and table in comments
- Implement idempotent ETL jobs
- Suggest data platform specific optimization SQL syntax

DON'T:
- Apply business logic or transformations
- Transform business values (standardize in DWD)
- Store without partitions
- Delete raw data prematurely
- Skip data quality checks
- Mix data from multiple sources in one ODS table

11. COMMON PITFALLS

Pitfall: Schema Drift
Solution: Implement schema evolution detection; alert on changes

Pitfall: Late Arriving Data
Solution: Allow reprocessing window (T+2); document cutoff times

Pitfall: Small Files
Solution: Configure file merge; target > 128MB per file

Pitfall: Partition Explosion
Solution: Use appropriate granularity; archive old partitions

12. RELATED DOCUMENTS

- docs/layers/DWD_DESIGN.md - Downstream layer specifications
- docs/standards/NAMING_CONVENTION.md - Naming standards
- docs/standards/SQL_STANDARDS.md - SQL coding standards
- docs/operations/RETENTION_POLICY.md - Data retention guidelines