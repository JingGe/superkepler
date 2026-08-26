# Data Warehouse Repository Template

Document ID: DATABRICKS_DW_REPO_TEMPLATE  
Last Updated: 2026-08-25  
Author: Jing Ge https://github.com/JingGe

---

## 1. DIRECTORY STRUCTURE

```
{project_name}/
├── databricks.yml                        # Databricks Asset Bundle (DAB) or Lakeflow config
├── sql/
│   ├── ods/                              # Raw landing — no domain subdirs, organized by source system
│   │   ├── ods_mysql_{table}_di.sql
│   │   └── ods_kafka_{topic}_hi.sql
│   ├── dim/                              # Cross-domain shared dimensions — no domain subdirs
│   │   ├── dim_user_info_df.sql
│   │   └── dim_product_detail_df.sql
│   ├── dwd/                              # Domain partitioning starts here
│   │   ├── trade/
│   │   │   └── dwd_trade_order_di.sql
│   │   ├── user/
│   │   │   └── dwd_user_login_di.sql
│   │   └── traffic/
│   │       └── dwd_traffic_page_view_di.sql
│   ├── dwm/                              # Optional layer — same domain structure as dwd/
│   │   └── trade/
│   │       └── dwm_trade_order_merge_di.sql
│   ├── dws/                              # Domain partitioning continues
│   │   ├── trade/
│   │   │   ├── dws_trade_order_1d_di.sql
│   │   │   └── dws_trade_order_7d_nd.sql
│   │   └── user/
│   │       └── dws_user_action_1d_di.sql
│   ├── ads/                              # No domain subdirs — organized by data mart
│   │   ├── exec/
│   │   │   └── ads_exec_kpi_daily_df.sql
│   │   └── mkt/
│   │       └── ads_mkt_campaign_result_di.sql
│   └── common/                           # Shared macros, lookup maps, reusable CTEs
│       └── status_code_map.sql
├── tests/                                # Validation queries — mirrors sql/ structure
│   ├── ods/
│   ├── dim/
│   ├── dwd/
│   │   └── trade/
│   └── dws/
│       └── trade/
└── docs/
    ├── domains/                          # One doc per business domain
    │   ├── trade.md
    │   └── user.md
    └── marts/                            # One doc per ADS data mart
        └── exec.md
```

### Directory rules

| Layer | Subdirectory scheme | Rationale |
|-------|---------------------|-----------|
| `ods/` | Flat — by source system | Mirrors source structure, no domain abstraction |
| `dim/` | Flat — by entity | Cross-domain, no single owner |
| `dwd/` | By business domain | Business process ownership starts here |
| `dwm/` | By business domain | Optional layer, same ownership model as dwd |
| `dws/` | By business domain | Aggregation stays within domain |
| `ads/` | By data mart | Consumer-facing, domain abstraction ends |

---

## 2. SQL FILE CONVENTIONS

One SQL file per table, named identically to the table: `dwd_trade_order_di.sql`.

Each file contains DDL + DML in sequence, with a mandatory header block.

### 2.1 File header (required for all files)

```sql
-- ============================================================================
-- Table:       {table_name}
-- Layer:       {ODS | DIM | DWD | DWM | DWS | ADS}
-- Domain:      {trade | user | traffic | product | finance | ...}  (DWD/DWS only)
-- Description: {business purpose of this table}
-- Platform:    {Databricks | Hive | Snowflake | BigQuery}
-- Pipeline:    {DAB | Lakeflow}
-- Author:      {name}
-- Created:     {YYYY-MM-DD}
-- Updated:     {YYYY-MM-DD}
-- Version:     1.0.0
-- ============================================================================
-- MODIFICATION HISTORY
-- {YYYY-MM-DD} | {author} | {description of change}
-- ============================================================================
```

### 2.2 DAB SQL file (INSERT OVERWRITE pattern)

Used when deploying via Databricks Asset Bundles. Each file contains `CREATE TABLE IF NOT EXISTS` followed by `INSERT OVERWRITE`.

```sql
-- ============================================================================
-- Table:       dwd_trade_order_di
-- Layer:       DWD
-- Domain:      trade
-- Description: Trade order fact table, atomic granularity, daily incremental
-- Platform:    Databricks
-- Pipeline:    DAB
-- ============================================================================

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.dwd_trade_order_di (
    order_id        STRING          NOT NULL COMMENT 'Order ID (Business Key)',
    user_id         STRING          COMMENT 'User ID',
    product_name    STRING          COMMENT 'Product Name (degenerated dimension)',
    order_amount    DECIMAL(18,2)   COMMENT 'Order Amount',
    order_status    STRING          COMMENT 'Order Status',
    is_paid         BOOLEAN         COMMENT 'Is Order Paid',
    create_time     TIMESTAMP       COMMENT 'Order Create Time',
    etl_time        TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id    STRING          COMMENT 'ETL Batch ID'
)
USING DELTA
CLUSTER BY (dt, order_status, user_id)
COMMENT 'DWD: trade order fact table, daily incremental'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);

-- Variable syntax:
--   Hive / Airflow:        ${biz_date}       (default, used below)
--   Databricks native SQL: ${var:biz_date}   (set with: SET VAR biz_date = '...';)

INSERT INTO {catalog}.{schema}.dwd_trade_order_di
REPLACE WHERE dt = '${biz_date}'
SELECT
    o.order_id,
    o.user_id,
    COALESCE(p.product_name, 'unknown')         AS product_name,
    COALESCE(o.order_amount, 0)                 AS order_amount,
    COALESCE(o.order_status, 'unknown')         AS order_status,
    CASE WHEN o.pay_time IS NOT NULL
         THEN TRUE ELSE FALSE END               AS is_paid,
    o.create_time,
    CURRENT_TIMESTAMP()                         AS etl_time,
    '${batch_id}'                               AS etl_batch_id,
    '${biz_date}'                               AS dt
FROM {catalog}.{schema}.ods_mysql_trade_orders_di  o
LEFT JOIN {catalog}.{schema}.dim_product_detail_df p
       ON o.product_id = p.product_id
      AND p.is_current = TRUE
WHERE o.dt          = '${biz_date}'
  AND o.order_id    IS NOT NULL
  AND o.order_amount > 0;
```

### 2.3 Lakeflow SQL file (declarative pattern)

Used when deploying via Lakeflow Pipelines. No `INSERT OVERWRITE` — Lakeflow manages incremental refresh automatically. DDL and query are combined in one `CREATE OR REFRESH` statement. Table references in `FROM STREAM(...)` or `FROM` build the DAG automatically.

```sql
-- ============================================================================
-- Table:       dwd_trade_order_di
-- Layer:       DWD
-- Domain:      trade
-- Description: Trade order fact table, atomic granularity, daily incremental
-- Platform:    Databricks
-- Pipeline:    Lakeflow
-- ============================================================================

CREATE OR REFRESH MATERIALIZED VIEW {catalog}.{schema}.dwd_trade_order_di
(
    CONSTRAINT order_id_not_null   EXPECT (order_id IS NOT NULL)   ON VIOLATION DROP ROW,
    CONSTRAINT order_amount_valid  EXPECT (order_amount > 0)        ON VIOLATION DROP ROW
)
CLUSTER BY (dt, order_status, user_id)
COMMENT 'DWD: trade order fact table, daily incremental'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
AS
SELECT
    o.order_id,
    o.user_id,
    COALESCE(p.product_name, 'unknown')         AS product_name,
    COALESCE(o.order_amount, 0)                 AS order_amount,
    COALESCE(o.order_status, 'unknown')         AS order_status,
    CASE WHEN o.pay_time IS NOT NULL
         THEN TRUE ELSE FALSE END               AS is_paid,
    o.create_time,
    CURRENT_TIMESTAMP()                         AS etl_time,
    CAST(o.create_time AS DATE)                 AS dt
FROM {catalog}.{schema}.ods_mysql_trade_orders_di  o  -- Lakeflow resolves upstream from table name
LEFT JOIN {catalog}.{schema}.dim_product_detail_df p
       ON o.product_id = p.product_id
      AND p.is_current = TRUE;
```

---

## 3. DATABRICKS ASSET BUNDLE CONFIG (`databricks.yml`)

DAB defines explicit task dependencies. Each layer is a task stage; tasks within a stage run in parallel.

```yaml
bundle:
  name: {project_name}

variables:
  catalog:
    default: dev
  schema:
    default: warehouse
  biz_date:
    default: "2026-01-01"

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://{workspace}.azuredatabricks.net
  prod:
    mode: production
    workspace:
      host: https://{workspace}.azuredatabricks.net

resources:
  jobs:
    warehouse_pipeline:
      name: warehouse_pipeline
      job_clusters:
        - job_cluster_key: default
          new_cluster:
            spark_version: 15.4.x-scala2.12
            node_type_id: Standard_DS3_v2
            num_workers: 2

      tasks:
        # ── Stage 1: ODS ──────────────────────────────────────────────────────
        - task_key: ods_mysql_trade_orders
          job_cluster_key: default
          sql_task:
            file:
              path: sql/ods/ods_mysql_trade_orders_di.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

        - task_key: ods_mysql_user_info
          job_cluster_key: default
          sql_task:
            file:
              path: sql/ods/ods_mysql_user_info_df.sql
            warehouse_id: {warehouse_id}

        # ── Stage 2: DIM ──────────────────────────────────────────────────────
        - task_key: dim_user_info
          depends_on:
            - task_key: ods_mysql_user_info
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dim/dim_user_info_df.sql
            warehouse_id: {warehouse_id}

        - task_key: dim_product_detail
          depends_on:
            - task_key: ods_mysql_trade_orders
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dim/dim_product_detail_df.sql
            warehouse_id: {warehouse_id}

        # ── Stage 3: DWD ──────────────────────────────────────────────────────
        - task_key: dwd_trade_order
          depends_on:
            - task_key: ods_mysql_trade_orders
            - task_key: dim_product_detail
            - task_key: dim_user_info
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dwd/trade/dwd_trade_order_di.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

        - task_key: dwd_user_login
          depends_on:
            - task_key: ods_mysql_user_info
            - task_key: dim_user_info
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dwd/user/dwd_user_login_di.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

        # ── Stage 4: DWS ──────────────────────────────────────────────────────
        - task_key: dws_trade_order_1d
          depends_on:
            - task_key: dwd_trade_order
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dws/trade/dws_trade_order_1d_di.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

        - task_key: dws_user_action_1d
          depends_on:
            - task_key: dwd_user_login
          job_cluster_key: default
          sql_task:
            file:
              path: sql/dws/user/dws_user_action_1d_di.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

        # ── Stage 5: ADS ──────────────────────────────────────────────────────
        - task_key: ads_exec_kpi_daily
          depends_on:
            - task_key: dws_trade_order_1d
            - task_key: dws_user_action_1d
          job_cluster_key: default
          sql_task:
            file:
              path: sql/ads/exec/ads_exec_kpi_daily_df.sql
            warehouse_id: {warehouse_id}
            parameters:
              biz_date: "{{job.parameters.biz_date}}"

      parameters:
        - name: biz_date
          default: "{{start_date}}"
```

---

## 4. LAKEFLOW PIPELINE CONFIG (`databricks.yml`)

Lakeflow builds the DAG automatically from table references. Each pipeline is pointed at a layer directory. Separate pipelines allow different refresh cadences per layer.

```yaml
bundle:
  name: {project_name}

variables:
  catalog:
    default: dev
  schema:
    default: warehouse

targets:
  dev:
    mode: development
    default: true
    workspace:
      host: https://{workspace}.azuredatabricks.net
  prod:
    mode: production
    workspace:
      host: https://{workspace}.azuredatabricks.net

resources:
  pipelines:
    # ── Pipeline 1: ODS — continuous streaming ────────────────────────────────
    ods_pipeline:
      name: ods_pipeline
      catalog: ${var.catalog}
      schema:  ${var.schema}
      continuous: true                    # streaming mode
      source_code_path: ./sql/ods         # Lakeflow reads all .sql files here
      clusters:
        - label: default
          num_workers: 2

    # ── Pipeline 2: DIM + DWD — triggered, hourly ────────────────────────────
    dwd_pipeline:
      name: dwd_pipeline
      catalog: ${var.catalog}
      schema:  ${var.schema}
      continuous: false
      trigger:
        cron:
          quartz_cron_expression: "0 0 * ? * *"   # every hour
          timezone_id: UTC
      source_code_path:
        - ./sql/dim                       # Lakeflow resolves dim -> dwd dependency automatically
        - ./sql/dwd
        - ./sql/dwm                       # optional; remove if dwm layer not used
      clusters:
        - label: default
          num_workers: 4

    # ── Pipeline 3: DWS — triggered, daily ───────────────────────────────────
    dws_pipeline:
      name: dws_pipeline
      catalog: ${var.catalog}
      schema:  ${var.schema}
      continuous: false
      trigger:
        cron:
          quartz_cron_expression: "0 0 2 ? * *"   # daily at 02:00 UTC
          timezone_id: UTC
      source_code_path: ./sql/dws
      clusters:
        - label: default
          num_workers: 2

    # ── Pipeline 4: ADS — triggered, daily ───────────────────────────────────
    ads_pipeline:
      name: ads_pipeline
      catalog: ${var.catalog}
      schema:  ${var.schema}
      continuous: false
      trigger:
        cron:
          quartz_cron_expression: "0 0 4 ? * *"   # daily at 04:00 UTC
          timezone_id: UTC
      source_code_path: ./sql/ads
      clusters:
        - label: default
          num_workers: 1
```

---

## 5. CHOOSING DAB VS. LAKEFLOW

| Criteria | DAB (Asset Bundles) | Lakeflow Pipelines |
|----------|--------------------|--------------------|
| SQL style | `INSERT OVERWRITE` / `REPLACE WHERE` | `CREATE OR REFRESH MATERIALIZED VIEW` |
| Dependency definition | Explicit `depends_on` in `databricks.yml` | Automatic — resolved from `FROM table_name` references |
| Incremental logic | You write the `WHERE dt = '${biz_date}'` filter | Lakeflow manages incremental refresh automatically |
| Data quality | Manual `WHERE` filters + post-load checks | Declarative `CONSTRAINT ... EXPECT ... ON VIOLATION` |
| Variable injection | `${biz_date}` from scheduler / Airflow | Not needed — Lakeflow tracks watermarks |
| Best for | Teams already using Airflow or complex cross-system orchestration | Greenfield Databricks-native pipelines |

---

## 6. ACTIVATION COMMAND

When the user asks to **create a new data warehouse repo**, use this template to:

1. Ask which project name
2. Ask which business domains are in scope (trade, user, traffic, product, finance, ...)
3. Ask which data marts are in scope for ADS (exec, mkt, crm, ops, ...)
4. Ask whether the DWM layer is needed
5. Ask whether to generate a `databricks.yml` pipeline config (optional — user may want SQL source code only)
   - If yes: ask DAB or Lakeflow
6. Generate the directory structure (substituting project name, domains, marts)
7. Generate one example `.sql` file per layer
   - If pipeline config requested: use the syntax for the chosen type (section 2.2 for DAB, 2.3 for Lakeflow)
   - If no pipeline config: use DAB syntax as the default (INSERT OVERWRITE pattern)
8. If pipeline config requested: generate `databricks.yml` using section 3 (DAB) or section 4 (Lakeflow)
