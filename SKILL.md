---
name: data-modeling-skill
description: Use this skill for any data warehouse or data lakehouse design task — including layered architecture design (medallion/bronze-silver-gold, Kimball dimensional modeling, Data Vault, Alibaba OneData), schema design (star schema, snowflake schema, fact and dimension tables), SQL code generation (DDL, staging/mart layer queries, incremental logic), and data modeling best practices for platforms like BigQuery, Snowflake, Redshift, or Databricks. Trigger this even when the user doesn't use these exact terms — if they're asking how to structure, organize, or model data across layers or zones (raw, curated, trusted, serving, ODS), or want dbt models or ELT pipeline SQL, this skill applies. Also trigger on commands like "Design table for", "Generate DDL for", or "Generate ETL for".
metadata: 
  version: 1.1.0
  Last Updated: 2026-04-08 
  Author: Jing Ge https://github.com/JingGe
---

# Data Modeling

This Data Modeling skill enables the design of structured, scalable, and efficient data schemas aligned with the layered data warehouse architecture (ODS, DWD, DWM, DWS, ADS). This skill translates business requirements into logical and physical data models, ensuring data integrity, query performance, and maintainability. It encompasses dimensional modeling, normalization, slowly changing dimension (SCD) strategies, and grain definition.

The skill ensures that all models adhere to the established naming conventions, layer responsibilities, and SQL standards defined in the architecture documentation. It bridges the gap between business needs and technical implementation by defining clear relationships, keys, and metrics.

Be precise and deterministic in SQL generation. Avoid creative variations. Prefer the most conventional, standards-compliant form for DDL and ETL patterns.

## Medallion Architecture Mapping
If users are using Spark or Databricks and confirmed to use the Medallion terminology, use the following mapping:

  - Bronze = ODS (Raw landing)
  - Silver = DWD / DWM / DIM (Atomic, cleaned rows)
  - Gold = DWS / ADS (Aggregates and KPI tables)

Strictly follow the references/NAMING_CONVENTION.md. ONLY when users confirmed they want to use medallion architecture, change the naming convention to use bronze / silver / gold to replace ODS / DWD / DWM / DIM / DWS / ADS. Remember this rule. 

## When to use this

Use this skill in the following scenarios:

1. Design data warehouse from scratch follow professional design principles and best practices.
2. Layered data modeling design leverage the medallion architecture, the Kimball architecture and Alibaba's OneData concept.
3. New Source Integration: When ingesting data from a new source system into the ODS layer.
4. Data model Improvement: When existing model requires to split and move sql logic into different layers to improve the flexibility, maintainability, and performance.
5. Performance Optimization: When existing queries are slow due to poor schema design, requiring denormalization or aggregation strategies.
6. Schema Evolution: When source systems change structure, requiring updates to DWD/DIM tables and SCD handling.
7. New Analytics Requirements: When business stakeholders request new metrics, reports, or dashboards requiring new DWS or ADS tables.
8. Data Mart Creation: When building subject-area specific data marts for specific departments (Finance, Marketing, Operations).
9. Refactoring: When cleaning up technical debt, inconsistent metrics, or redundant tables in the warehouse.

## REFERENCE DOCUMENTS:

Always consult these documents when making design decisions:
  - docs/layers/ODS_DESIGN.md - ODS layer specifications
  - docs/layers/DWD_DESIGN.md - DWD layer specifications
  - docs/layers/DIM_DESIGN.md - DIM specifications
  - docs/layers/DWM_DESIGN.md - DWM layer specifications
  - docs/layers/DWS_DESIGN.md - DWS layer specifications
  - docs/layers/ADS_DESIGN.md - ADS layer specifications
  - docs/standards/NAMING_CONVENTION.md - Naming standards
  - docs/standards/SQL_STANDARDS.md - SQL coding standards

CORE ARCHITECTURE STANDARDS:

  Layer Responsibilities:
  - ODS (ods_): Raw data ingestion, minimal cleaning. Preserve source structure. Partition by dt.
  - DIM (dim_): Conformed dimensions (Master Data). Handle SCD (Type 1/2). Source of truth for joins.
  - DWD (dwd_): Cleaned detail facts, standardized logic. Atomic granularity. Star schema. 
  - DWM (dwm_): Mid-level aggregation, business logic application. Bridge between DWD and DWS. DWM is optional layer.
  - DWS (dws_): Aggregated topic-wide tables. Pre-compute metrics (1d, 7d, 30d).
  - ADS (ads_): Application-specific data products. Optimized for BI/API/Reports.

Layer Flow (Unidirectional):
  Source Systems -> ODS -> DWD -> DWM -> DWS -> ADS -> BI/API/ML
  
Rules:
  - ODS -> DWD -> DWM -> DWS -> ADS (Allowed)
  - ADS -> ODS (Never bypass layers)
  - DWS -> ODS (Never skip DWD/DWM)

Loading Strategy Suffixes:
  - di: Daily Incremental (Once per day, T+1)
  - df: Daily Full Snapshot (Once per day, T+1)
  - hi: Hourly Incremental (Every hour)
  - hf: Hourly Full Snapshot (Every hour)
  - nd: N-Day Rolling (Daily, for DWS cumulative windows)
  - rt: Real-Time (Streaming)
  - full: Static Load (One-time)

SQL GENERATION GUIDELINES:

  General Rules:
  - Idempotency: Use INSERT OVERWRITE for batch jobs
  - Null Safety: Handle NULLs explicitly with COALESCE
  - Comments: Every column and table must have comments
  - CTEs: Use WITH clauses for complex logic
  - Variables: Use ${biz_date} or {{ ds }} for dates

  DDL Standard Format:
  CREATE TABLE IF NOT EXISTS {table_name} (
      column_name     DATA_TYPE     COMMENT 'Column description',
      ...
  )
  COMMENT 'Table description'
  PARTITIONED BY (dt STRING)
  STORED AS PARQUET
  TBLPROPERTIES ('parquet.compression' = 'SNAPPY');

  ETL Standard Format:
  INSERT OVERWRITE TABLE {target_table} PARTITION(dt='${biz_date}')
  SELECT 
      COALESCE(column, 0) AS column,
      ...
  FROM {source_table}
  WHERE dt = '${biz_date}'
    AND primary_key IS NOT NULL;

## INTERACTION WORKFLOW:

  Step 1: Analyze Requirements
  Interactive mode: Ask clarifying questions before proceeding:
  - What is the data source?
  - How does the data source schema look like?
  - What is the business purpose of this table?
  - What is the expected update frequency?
  - What is the granularity?
  - Do we need to track historical changes (SCD)? (only relevant for dim_ tables)
  - Which data platform will be used (e.g. Databricks, Snowflake, BigQuery)? All generated SQL must conform to the selected platform's standards.
  - Confirm whether medallion architecture should be used. If yes, apply the Medallion Architecture Mapping.

  Non-interactive / agentic / batch mode: If context already contains enough information to proceed (source schema, business purpose, platform, etc.), infer from available information, make reasonable assumptions, and state those assumptions explicitly in the DESIGN NOTES section. Do not block on missing information — proceed and flag gaps.

  Step 2: Design Architecture
  Propose:
  - Layer assignment(after identifying the layers, only load related design md file from the references. Don't loadd all of them.)
  - Table name (following naming convention)
  - Columns and data types
  - Partition strategy
  - Loading strategy suffix
  - Use assets/SQL_TEMPLATE.md to generate SQL scripts

  Step 3: Generate DDL
  Use assets/SQL_TEMPLATE.md to generate SQL scripts and provide complete CREATE TABLE statement with:
  - All columns with data types
  - Comments on every column
  - Table-level comment
  - Partition definition
  - Storage format and compression

  Step 4: Generate DML and ETL
  Use assets/SQL_TEMPLATE.md to generate SQL scripts and provide INSERT OVERWRITE logic showing:
  - Source tables
  - Transformation logic
  - Data quality checks
  - Partition handling
  - Choose the right Loading Strategy. Keep asking questions until having enough information to decide which loading strategy is correct

  Step 5: Explain Choices
  Explain:
  - Why this layer was chosen
  - Why this loading strategy was selected
  - Optimization considerations
  - Lifecycle/retention recommendations
  - Explain the design thoughts with details

## OUTPUT Format:

The output must be structured in Markdown format with the following sections:

1. ARCHITECTURE DESIGN
  [Table with Layer, Table Name, Description, Loading Strategy]

2. DDL (CREATE TABLE)
  [SQL code block]

3. ETL LOGIC (SOURCE -> TARGET)
  [SQL code block]

4. DESIGN NOTES
  - Partitioning: ...
  - SCD Strategy: ... (only need  for dim_ table)
  - Optimization: ...
  - Retention: ...
  - Assumptions (agentic mode): list any assumptions made when context was incomplete

5. SQL File Generation
Ask users if they would like to generate SQL files directly. If users answer with "y" or "yes", generate SQL files according to the design directly.

## ACTIVATION COMMANDS (optional shortcuts)
These commands can be used to invoke specific workflows directly. They are optional — the skill also triggers automatically from context.

  - "Activate data modeling Skill" — Enable this skill
  - "Design table for [requirement]" — Start table design workflow
  - "Generate DDL for [table_name]" — Generate CREATE TABLE statement
  - "Generate ETL for [source] -> [target]" — Generate transformation SQL
  - "Review data modeling architecture" — Audit existing table designs

## CONSTRAINTS & SAFETY:
  - Never suggest DROP TABLE without explicit confirmation
  - Never suggest ADS querying ODS directly
  - Always warn about data skew on high-cardinality GROUP BY
  - Ensure partition columns are excluded from SELECT in INSERT OVERWRITE PARTITION
  - Every table must have metadata documentation

## QUALITY CHECKLIST:
  [] Table name follows naming convention  
  [] Loading strategy suffix is correct  
  [] All columns have comments  
  [] Table has a comment  
  [] Partition column is defined  
  [] Storage format is specified  
  [] ETL is idempotent  
  [] Null handling is implemented  
  [] Data quality checks are included  
  [] Layer flow is respected (no bypass)  