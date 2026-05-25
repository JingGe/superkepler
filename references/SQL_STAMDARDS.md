SQL CODING STANDARDS


Document ID: SQL-CODING-STANDARDS 
Last Updated: 2026-05-25   
Author: Jing Ge https://github.com/JingGe  


1. OVERVIEW


This document defines the SQL coding standards for all ETL/ELT processes. Adherence to these standards ensures:

- Readability: Easy to understand and maintain
- Consistency: Uniform style across all jobs
- Quality: Reduced errors and bugs
- Automation: Easier to parse and validate
- Idempotency: Jobs can be retried safely without duplicating data.
- Observability: Lineage and auditing are built into every table.
- Performance: Leveraging Delta Lake features like Liquid Clustering and Predictive Optimization.
- Governance: Consistent naming across Catalog, Schema, and Column levels.

2. GENERAL SQL RULES


2.1 Formatting Rules

| Rule                    | Description
| ------------------------| --------------------------------------
| Keywords                | UPPERCASE (SELECT, FROM, WHERE)
| Identifiers             | lowercase (table_name, column_name)
| Indentation             | 4 spaces per level
| Line Length             | Max 120 characters
| Aliases	              | Required & Meaningful(FROM fact_orders AS f)
| Trailing Commas         | Leading or Trailing. Be consistent within the team

2.2 Comment Rules

| Rule                    | Description
| ------------------------| --------------------------------------
| Table Comments          | Required on all tables
| Column Comments         | Required on all columns
| Complex Logic           | Inline comments explaining why
| CTE Names               | Descriptive names
| Business Rules          | Document source of business logic

3. DDL STANDARDS


3.1 CREATE TABLE Format

```sql
CREATE TABLE IF NOT EXISTS {table_name} (
    -- Business Keys
    column_name         DATA_TYPE       COMMENT 'Description',
    
    -- Metrics
    metric_name         DATA_TYPE       COMMENT 'Description',
    
    -- Audit Fields
    etl_time            TIMESTAMP       COMMENT 'ETL timestamp'
)
COMMENT 'Table description'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
```

3.2 Column Ordering

Order columns in this sequence:
1. Business keys (id fields)
2. Dimension attributes
3. Metrics (counts, amounts)
4. Time fields
5. Status/flag fields
6. Audit fields

3.3 Unity Catalog & Delta

Always reference tables using the full path: {catalog}.{schema}.{table}. Example: prod.traffic.dwd_order_di

Prioritize Liquid Clustering over static partitioning for improved maintenance and query speed.

```sql
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} (
    -- 1. Business Keys (NOT NULL)
    order_id          STRING          NOT NULL COMMENT 'Primary Business Key',
    
    -- 2. Dimensions (dim_ prefix)
    dim_region        STRING          COMMENT 'Hierarchy L1: Geographic Region',
    dim_category      STRING          COMMENT 'Product Category',
    
    -- 3. Metrics (Explicit Precision)
    pay_amt           DECIMAL(18,2)   DEFAULT 0 COMMENT 'Total paid amount in USD',
    tax_amt           DECIMAL(18,2)   DEFAULT 0 COMMENT 'Tax amount',
    
    -- 4. Audit Fields
    etl_inserted_at   TIMESTAMP       DEFAULT current_timestamp() COMMENT 'Record creation time',
    etl_updated_at    TIMESTAMP       COMMENT 'Last update time',
    dt                DATE            NOT NULL COMMENT 'Business Date (Clustering Key)'
)
USING DELTA
CLUSTER BY (dt, dim_region) -- Optimized for date-range and regional filters
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);
```

4. ETL STANDARDS


4.1 Idempotent Write Strategy

Every ETL job must be "Re-runnable." Use INSERT OVERWRITE for daily snapshots or MERGE for accumulating snapshots.

```sql
INSERT OVERWRITE TABLE {target_table} PARTITION(dt='${biz_date}')
SELECT 
    -- Business Keys
    user_id,
    order_id,
    
    -- Metrics with null safety
    COALESCE(order_amount, 0) AS order_amount,
    COALESCE(order_cnt, 0) AS order_cnt,
    
    -- Derived fields
    CASE 
        WHEN order_amount > 1000 THEN 'high_value'
        ELSE 'normal'
    END AS order_tier,
    
    -- Audit fields
    CURRENT_TIMESTAMP() AS etl_time,
    '${batch_id}' AS etl_batch_id
FROM {source_table}
WHERE dt = '${biz_date}'
  AND business_key IS NOT NULL;
```
4.2 Safe Division (Null Safety)

Never divide without NULLIF.

- Bad: SUM(amt) / COUNT(id) — (Fails if count is 0)
- Good: SUM(amt) / NULLIF(COUNT(id), 0)

4.3 CTE Usage

Use CTEs for readability, especially for complex joins. Rule: CTE names must be verbs or descriptive nouns.

```sql
WITH 
cleaned_data AS (
    SELECT 
        user_id,
        COALESCE(amount, 0) AS amount
    FROM ods_source
    WHERE dt = '${biz_date}'
),
aggregated_data AS (
    SELECT 
        user_id,
        SUM(amount) AS total_amount
    FROM cleaned_data
    GROUP BY user_id
)
INSERT OVERWRITE TABLE target PARTITION(dt='${biz_date}')
SELECT * FROM aggregated_data;
```

4.3 Join Standards

```sql
-- Use explicit JOIN syntax
SELECT 
    f.order_id,
    d.user_name
FROM dwd_fact f
LEFT JOIN dim_dimension d 
    ON f.user_id = d.user_id 
    AND d.is_current = TRUE
WHERE f.dt = '${biz_date}';

-- Avoid implicit joins (comma-separated tables)
-- BAD: FROM table1, table2 WHERE table1.id = table2.id
```

5. NULL HANDLING


5.1 Metric Columns

Always use COALESCE for metrics:

COALESCE(column, 0) AS column

5.2 String Columns

Use COALESCE for strings:

COALESCE(column, 'unknown') AS column

5.3 Boolean Columns

Use explicit boolean handling:

CASE WHEN column = 1 THEN TRUE ELSE FALSE END AS is_active

6. DATA QUALITY CHECKS


6.1 Mandatory Checks

Include in all ETL jobs:

WHERE primary_key IS NOT NULL
  AND business_date IS NOT NULL
  AND amount >= 0

6.2 Validation Queries

Run after ETL:

SELECT 
    COUNT(*) AS total_count,
    COUNT(CASE WHEN amount < 0 THEN 1 END) AS negative_count,
    COUNT(CASE WHEN key IS NULL THEN 1 END) AS null_key_count
FROM target_table
WHERE dt = '${biz_date}';

7. PERFORMANCE OPTIMIZATION


7.1 Partition Pruning

Always filter by partition:

WHERE dt = '${biz_date}'          -- Good
WHERE dt >= '${biz_date}'         -- Good for ranges
-- No WHERE on dt                -- Bad (full table scan)

7.2 Join Optimization

-- Put smaller table on left for broadcast join
SELECT /*+ BROADCAST(d) */
    f.*,
    d.dimension_attr
FROM large_fact f
JOIN small_dim d ON f.id = d.id;

Scope the Target: When merging, always include the clustering/partition key in the ON clause to limit the scan.

Explicit Joins: Only use INNER, LEFT, RIGHT, or FULL OUTER. Never use comma-separated tables.

Broadcast Hint: Use /*+ BROADCAST(small_table) */ when joining a large fact to a small dimension (< 1GB).

7.3 Aggregation Optimization

-- Pre-filter before aggregation
SELECT 
    user_id,
    SUM(amount) AS total
FROM table
WHERE dt = '${biz_date}'          -- Filter first
  AND amount > 0
GROUP BY user_id;

7.4 Databricks SQL Optimization

USING DELTA

In Databricks, this explicitly tells the engine to use the Delta Lake format, enabling features like:

- Time Travel: SELECT * FROM table VERSION AS OF 10.
- ACID Transactions: Ensuring your dashboard doesn't show partial data while the ETL is running.
- Schema Evolution: Allowing you to add columns without rebuilding the table.

CLUSTER BY (Liquid Clustering)

It replaces partitioning and Z-Ordering. It keeps the data physically grouped by report_date and dim_region automatically. This makes your dashboard filters lightning-fast without you having to manage file sizes.

8. ERROR HANDLING


8.1 Transaction Handling

For engines that support transactions:

BEGIN TRANSACTION;

INSERT OVERWRITE TABLE target ...

-- Validate
IF (SELECT COUNT(*) FROM target WHERE dt='${biz_date}') = 0 THEN
    ROLLBACK;
    RAISE ERROR 'ETL produced no results';
END IF;

COMMIT;

8.2 Logging

Log ETL execution:

INSERT INTO etl_job_log (
    job_name,
    start_time,
    end_time,
    status,
    record_count,
    error_message
) VALUES (
    '${job_name}',
    '${start_time}',
    CURRENT_TIMESTAMP(),
    '${status}',
    '${record_count}',
    '${error_message}'
);

9. NAMING IN SQL

9.1 Alias Rules

-- Use meaningful aliases
SELECT 
    f.order_id,
    f.order_amount,
    d.user_name
FROM dwd_fact f        -- f for fact
LEFT JOIN dim_user d   -- d for dimension

-- Avoid single letter aliases for complex queries
-- BAD: SELECT a.col1, b.col2 FROM table1 a, table2 b

9.2 Column Aliases

-- Always alias calculated columns
SELECT 
    SUM(amount) AS total_amount,      -- Good
    SUM(amount)                        -- Bad
FROM table;

10. VERSION CONTROL


10.1 SQL File Organization

Directory Structure:
sql/
  ods/
  dim/
  dwd/
  dwm/
  dws/
  ads/
  common/           -- Shared CTEs and functions
  tests/            -- Validation queries

10.2 Change Documentation

Add header to each SQL file:

-- ============================================================================
-- File: dwd_trade_order_di.sql
-- Layer: DWD
-- Description: Order fact table ETL
-- Author: {name}
-- Created: {date}
-- Last Modified: {date}
-- Version: 1.0.0
-- ============================================================================

Table Versioning: For breaking changes (removing columns), create a new table with _v2 and use a View to bridge the migration.

Logic Changes: Document logic changes in the SQL Header:

-- MODIFICATION HISTORY
-- 2026-03-22 | Jing | Updated GMV logic to exclude returned orders

11. TESTING STANDARDS


11.1 Unit Tests

Test each transformation:

-- Test null handling
SELECT COUNT(*) FROM target 
WHERE dt = '${biz_date}' 
  AND amount IS NULL;  -- Should be 0

-- Test business rules
SELECT COUNT(*) FROM target 
WHERE dt = '${biz_date}' 
  AND amount < 0;  -- Should be 0

11.2 Integration Tests

Test end-to-end flow:

-- Compare source and target counts
SELECT 
    'source' AS layer,
    COUNT(*) AS cnt
FROM ods_source WHERE dt = '${biz_date}'
UNION ALL
SELECT 
    'target' AS layer,
    COUNT(*) AS cnt
FROM dwd_target WHERE dt = '${biz_date}';

12. COMMON PATTERNS


12.1 SCD Type 2 Pattern

INSERT OVERWRITE TABLE dim_user_df PARTITION(dt='${biz_date}')
SELECT 
    COALESCE(new.user_id, old.user_id) AS user_id,
    COALESCE(new.user_name, old.user_name) AS user_name,
    CASE 
        WHEN old.user_id IS NULL THEN '${biz_date}'
        WHEN old.is_current = TRUE AND new.city != old.city THEN '${biz_date}'
        ELSE old.start_date 
    END AS start_date,
    CASE 
        WHEN old.is_current = TRUE AND new.city != old.city THEN DATE_SUB('${biz_date}', 1)
        ELSE old.end_date 
    END AS end_date,
    CASE 
        WHEN old.is_current = TRUE AND new.city != old.city THEN FALSE
        ELSE TRUE 
    END AS is_current
FROM dim_user_df old
FULL OUTER JOIN ods_user new 
    ON old.user_id = new.user_id 
    AND old.is_current = TRUE
WHERE old.is_current = TRUE OR new.user_id IS NOT NULL;

12.2 Scoped Merge (Accumulating Snapshot)

MERGE INTO dwd_trade_order_lifecycle AS t
USING ods_pg_order_di AS s
ON t.order_id = s.order_id 
   AND t.dt = s.order_create_date -- Scope to the born-on partition
WHEN MATCHED THEN 
    UPDATE SET 
        t.pay_time = COALESCE(t.pay_time, s.event_time),
        t.etl_updated_at = current_timestamp()
WHEN NOT MATCHED THEN 
    INSERT *;

13. RELATED DOCUMENTS

- references/ODS_DESIGN.md - ODS layer specifications
- references/DWD_DESIGN.md - DWD layer specifications
- references/DWM_DESIGN.md - DWM layer specifications
- references/DIM_DESIGN.md - DIM layer specifications
- references/DWS_DESIGN.md - DWS layer specifications
- references/ADS_DESIGN.md - ADS layer specifications
- references/NAMING_CONVENTION.md - Naming standards
- references/STAR_SCHEMA_DESIGN.md - Star schema design specification