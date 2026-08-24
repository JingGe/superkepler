-- ============================================================================
-- SQL JOB METADATA
-- ============================================================================
-- Table Name:     [layer]_[domain]_[entity]_[granularity]_[suffix]
-- Version:        1.0.0
-- Author:         [Your Name]
-- Created Date:   [YYYY-MM-DD]
-- Last Updated:   [YYYY-MM-DD]
-- Description:    [Brief description of table purpose, business logic, and key metrics] [Example: This table stores daily aggregated user behavior metrics for 
   marketing campaign analysis. It combines login events and transaction data.]
-- ============================================================================

-- ============================================================================
SECURITY & GOVERNANCE
  ------------------------------------------------------------------------------
  PII Level         : [Low | Medium | High | Critical]
  Data Classification : [Public | Internal | Confidential]
  Compliance Tags   : [GDPR | CCPA | HIPAA | SOC2 | None]
  Access Groups     : [group_analysts], [group_data_science]
-- ============================================================================

-- ============================================================================
  REVISION HISTORY
  ----------------------------------------------------------------------------
  Version   Date          Author              Description of Changes          
  --------  ------------  ------------------  --------------------------------  
  1.0.0     YYYY-MM-DD    [Name]              Initial Draft                   
  1.0.1     YYYY-MM-DD    [Name]              [e.g., Added ZORDER clustering] 
  1.0.2     YYYY-MM-DD    [Name]              [e.g., Updated SCD Type 2]      
-- ============================================================================

-- ============================================================================
-- PART 1: DDL (DATA DEFINITION LANGUAGE)
-- ============================================================================
-- Purpose: Create table structure with proper partitioning and storage
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 1.1: DROP EXISTING TABLE (IF RECREATING)
-- ----------------------------------------------------------------------------
-- WARNING: Only uncomment if you intend to drop and recreate the table
-- This will delete all existing data!

-- DROP TABLE IF EXISTS [layer]_[domain]_[entity]_[granularity]_[suffix];

-- Set the current catalog and schema for the session
-- Replace with your actual Unity Catalog and Schema names
SET CATALOG [catalog_name];
USE SCHEMA [schema_name];

-- ----------------------------------------------------------------------------
-- STEP 1.2: CREATE TABLE STATEMENT
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS [layer]_[domain]_[entity]_[granularity]_[suffix] (
    -- =========================================================================
    -- BUSINESS KEYS (Identifiers)
    -- =========================================================================
    [business_key_1]      STRING NOT NULL COMMENT 'Business key 1 (e.g., user_id)',
    [business_key_2]      STRING COMMENT 'Business key 2 (e.g., order_id)',
    
    -- =========================================================================
    -- DIMENSION ATTRIBUTES (Descriptive fields)
    -- =========================================================================
    [attr_column_1]       STRING          COMMENT '[Description of attribute 1]',
    [attr_column_2]       STRING          COMMENT '[Description of attribute 2]',
    [attr_column_3]       STRING          COMMENT '[Description of attribute 3]',
    
    -- =========================================================================
    -- METRICS (Measurable values)
    -- =========================================================================
    [metric_cnt_1]        BIGINT          COMMENT '[Description of count metric 1]',
    [metric_cnt_2]        BIGINT          COMMENT '[Description of count metric 2]',
    [metric_amt_1]        DECIMAL(18,2)   COMMENT '[Description of amount metric 1]',
    [metric_amt_2]        DECIMAL(18,2)   COMMENT '[Description of amount metric 2]',
    [metric_rate_1]       DECIMAL(5,4)    COMMENT '[Description of rate metric 1]',

    -- =========================================================================
    -- COMPUTED COLUMNS (Optional - Spark 3.4+)
    -- =========================================================================
    -- [computed_col]      STRING GENERATED ALWAYS AS (CONCAT([attr_column_1], '_suffix')),
    
    -- =========================================================================
    -- TIME DIMENSIONS
    -- =========================================================================
    -- [event_timestamp]     TIMESTAMP COMMENT 'Event occurrence time',
    -- [processing_date]     DATE COMMENT 'Processing date partition',
    [time_column_1]       TIMESTAMP       COMMENT '[Description of time column 1]',
    [time_column_2]       TIMESTAMP       COMMENT '[Description of time column 2]',
    [date_column_1]       STRING          COMMENT '[Description of date column 1]',
    
    -- =========================================================================
    -- STATUS & FLAGS
    -- =========================================================================
    [status_column_1]     STRING          COMMENT '[Description of status column 1]',
    [flag_column_1]       BOOLEAN         COMMENT '[Description of flag column 1]',
    [flag_column_2]       BOOLEAN         COMMENT '[Description of flag column 2]',
    
    -- =========================================================================
    -- SCD TYPE 2 FIELDS (Only for DIM tables with history tracking)
    -- =========================================================================
    -- start_date          STRING          COMMENT 'SCD: Effective start date',
    -- end_date            STRING          COMMENT 'SCD: Effective end date',
    -- is_current          BOOLEAN         COMMENT 'SCD: Is current version',
    -- version_id          BIGINT          COMMENT 'SCD: Version number',
    
    -- =========================================================================
    -- AUDIT FIELDS (Required for all tables)
    -- =========================================================================
    etl_create_time       TIMESTAMP       COMMENT 'ETL: Record creation timestamp',
    etl_update_time       TIMESTAMP       COMMENT 'ETL: Record update timestamp',
    etl_batch_id          STRING          COMMENT 'ETL: Batch job identifier',
    etl_source_system     STRING          COMMENT 'ETL: Source system name'
)
COMMENT '[Full table description: purpose and content summary]'
PARTITIONED BY (dt STRING)
USING PARQUET
OPTIONS (
    'parquet.compression' = 'SNAPPY',
    'external.table.purge' = 'FALSE'
);

-- ----------------------------------------------------------------------------
-- STEP 1.3: CREATE VIEWS (FOR ACCESS CONTROL)
-- ----------------------------------------------------------------------------

-- Public view (restricted columns)
CREATE OR REPLACE VIEW v_[layer]_[entity]_public AS
SELECT 
    [id_column_1],
    [attr_column_1],
    [metric_cnt_1],
    [metric_amt_1],
    dt
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE is_current = TRUE OR is_current IS NULL;

-- Restricted view (all columns including PII)
-- CREATE OR REPLACE VIEW v_[layer]_[entity]_restricted AS
-- SELECT * FROM [layer]_[domain]_[entity]_[granularity]_[suffix];

-- ============================================================================
-- PART 2: DML (DATA MANIPULATION LANGUAGE)
-- ============================================================================
-- Purpose: Load and transform data into the table
-- ============================================================================

-- ----------------------------------------------------------------------------
-- STEP 2.1: SET EXECUTION PARAMETERS
-- ----------------------------------------------------------------------------

-- Variable syntax differs by platform:
--   Hive / Airflow / dbt:    ${biz_date}               (used throughout this template)
--   Databricks SQL native:   ${var:biz_date}            (set with SET VAR syntax below)
--   Databricks SQL native:   SET VAR biz_date = '...';  (Databricks 12.2+)
--
-- If running in Databricks, replace ${biz_date} references below with ${var:biz_date}
-- and use the Databricks-native SET VAR syntax shown here.

-- Hive / Airflow style (default):
-- ${biz_date} is injected by the scheduler (e.g., Airflow: {{ ds }})

-- Databricks native style (uncomment when using Databricks SQL):
-- SET VAR biz_date    = '2026-03-28';
-- SET VAR batch_id    = 'ETL_20260328_001';
-- SET VAR source_system = 'MYSQL_PROD';

-- Performance tuning parameters (Spark / Databricks)
SET spark.sql.shuffle.partitions=300;
SET spark.sql.autoBroadcastJoinThreshold=104857600;

-- ----------------------------------------------------------------------------
-- STEP 2.2: DATA QUALITY CHECKS (PRE-LOAD)
-- ----------------------------------------------------------------------------

-- Check source data availability
SELECT 
    'SOURCE_DATA_CHECK' AS check_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT [id_column_1]) AS distinct_keys
FROM [source_table_name]
WHERE dt = '${biz_date}'
HAVING COUNT(*) = 0;
-- Should return 0 rows. If returns rows, source data is missing.

-- Check for duplicate keys in source
SELECT 
    'DUPLICATE_KEY_CHECK' AS check_name,
    [id_column_1],
    COUNT(*) AS dup_count
FROM [source_table_name]
WHERE dt = '${biz_date}'
GROUP BY [id_column_1]
HAVING COUNT(*) > 1;
-- Should return 0 rows. If returns rows, investigate duplicates.

-- ----------------------------------------------------------------------------
-- STEP 2.3: MAIN ETL - INSERT OVERWRITE (PARTITIONED TABLES)
-- ----------------------------------------------------------------------------

INSERT OVERWRITE TABLE [layer]_[domain]_[entity]_[granularity]_[suffix] 
PARTITION(dt='${biz_date}')
SELECT 
    -- ========================================================================
    -- BUSINESS KEYS
    -- ========================================================================
    src.[id_column_1],
    src.[id_column_2],
    
    -- ========================================================================
    -- DIMENSION ATTRIBUTES (with null handling)
    -- ========================================================================
    COALESCE(src.[attr_column_1], 'unknown') AS [attr_column_1],
    COALESCE(src.[attr_column_2], 'unknown') AS [attr_column_2],
    COALESCE(src.[attr_column_3], 'unknown') AS [attr_column_3],
    
    -- ========================================================================
    -- METRICS (with null safety and calculations)
    -- ========================================================================
    COALESCE(src.[metric_cnt_1], 0) AS [metric_cnt_1],
    COALESCE(src.[metric_cnt_2], 0) AS [metric_cnt_2],
    COALESCE(src.[metric_amt_1], 0) AS [metric_amt_1],
    COALESCE(src.[metric_amt_2], 0) AS [metric_amt_2],
    ROUND(
        COALESCE(src.[metric_amt_1], 0) / NULLIF(COALESCE(src.[metric_cnt_1], 0), 0), 
        4
    ) AS [metric_rate_1],
    
    -- ========================================================================
    -- TIME DIMENSIONS
    -- ========================================================================
    src.[time_column_1],
    src.[time_column_2],
    TO_DATE(src.[time_column_1]) AS [date_column_1],
    
    -- ========================================================================
    -- STATUS & FLAGS
    -- ========================================================================
    COALESCE(src.[status_column_1], 'pending') AS [status_column_1],
    CASE WHEN src.[flag_column_1] = 1 THEN TRUE ELSE FALSE END AS [flag_column_1],
    CASE WHEN src.[metric_amt_1] > 1000 THEN TRUE ELSE FALSE END AS [flag_column_2],
    
    -- ========================================================================
    -- SCD TYPE 2 FIELDS (Only for DIM tables)
    -- ========================================================================
    -- '${biz_date}' AS start_date,
    -- '9999-12-31' AS end_date,
    -- TRUE AS is_current,
    -- 1 AS version_id,
    
    -- ========================================================================
    -- AUDIT FIELDS
    -- ========================================================================
    CURRENT_TIMESTAMP() AS etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    '${source_system}' AS etl_source_system,
    -- user dynamic partitioning
    -- date_format(date_sub(current_date(), 1), 'yyyy-MM-dd') AS dt

FROM [source_table_name] src
[LEFT JOIN dim_[entity]_info_df dim ON src.[join_key] = dim.[join_key] AND dim.is_current = TRUE]
WHERE src.dt = '${biz_date}'
  AND src.[id_column_1] IS NOT NULL
  AND src.[id_column_1] != ''
  -- Add additional business rule filters
  AND src.[metric_amt_1] >= 0
  -- AND src.[status_column_1] IN ('active', 'completed', 'paid')
GROUP BY 
    src.[id_column_1],
    src.[id_column_2],
    src.[attr_column_1],
    src.[attr_column_2],
    src.[attr_column_3],
    src.[metric_cnt_1],
    src.[metric_cnt_2],
    src.[metric_amt_1],
    src.[metric_amt_2],
    src.[time_column_1],
    src.[time_column_2],
    src.[status_column_1],
    src.[flag_column_1];

-- ----------------------------------------------------------------------------
-- STEP 2.4: ALTERNATIVE - SCD TYPE 2 MERGE (FOR DIM TABLES)
-- ----------------------------------------------------------------------------
-- Uncomment and modify for dimension tables with history tracking

/*
-- Step 2.4.1: Identify changes
WITH source_data AS (
    SELECT * FROM ods_[entity]_info_df WHERE dt = '${biz_date}'
),
current_dims AS (
    SELECT * FROM [layer]_[domain]_[entity]_[granularity]_[suffix] 
    WHERE is_current = TRUE
),
changes AS (
    SELECT 
        s.[id_column_1],
        s.[attr_column_1],
        c.[attr_column_1] AS old_attr_column_1
    FROM source_data s
    LEFT JOIN current_dims c ON s.[id_column_1] = c.[id_column_1]
    WHERE c.[id_column_1] IS NULL  -- New records
       OR s.[attr_column_1] != c.[attr_column_1]  -- Changed attributes
)

-- Step 2.4.2: Close old records
INSERT INTO TABLE [layer]_[domain]_[entity]_[granularity]_[suffix] 
PARTITION(dt='${biz_date}')
SELECT 
    c.[id_column_1],
    c.[attr_column_1],
    c.start_date,
    DATE_SUB('${biz_date}', 1) AS end_date,
    FALSE AS is_current,
    c.version_id,
    c.etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    c.etl_source_system
FROM current_dims c
INNER JOIN changes ch ON c.[id_column_1] = ch.[id_column_1];

-- Step 2.4.3: Insert new/updated records
INSERT INTO TABLE [layer]_[domain]_[entity]_[granularity]_[suffix] 
PARTITION(dt='${biz_date}')
SELECT 
    ch.[id_column_1],
    ch.[attr_column_1],
    '${biz_date}' AS start_date,
    '9999-12-31' AS end_date,
    TRUE AS is_current,
    COALESCE((SELECT MAX(version_id) + 1 FROM [layer]_[domain]_[entity]_[granularity]_[suffix] 
              WHERE [id_column_1] = ch.[id_column_1]), 1) AS version_id,
    CURRENT_TIMESTAMP() AS etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    '${source_system}' AS etl_source_system
FROM changes ch;
*/

-- ----------------------------------------------------------------------------
-- STEP 2.5: ALTERNATIVE - ROLLING WINDOW AGGREGATION (FOR DWS nd TABLES)
-- ----------------------------------------------------------------------------
-- Uncomment and modify for DWS rolling window tables (7d, 30d, etc.)

/*
INSERT OVERWRITE TABLE [layer]_[domain]_[entity]_[granularity]_[suffix] 
PARTITION(dt='${biz_date}')
SELECT 
    [id_column_1],
    SUM([metric_cnt_1]) AS [metric_cnt_1]_nd,
    SUM([metric_cnt_2]) AS [metric_cnt_2]_nd,
    SUM([metric_amt_1]) AS [metric_amt_1]_nd,
    SUM([metric_amt_2]) AS [metric_amt_2]_nd,
    COUNT(1) AS days_active,
    MAX([time_column_1]) AS last_[time_column_1],
    CURRENT_TIMESTAMP() AS etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    '${source_system}' AS etl_source_system
FROM [layer]_[domain]_[entity]_1d_di
WHERE dt >= DATE_SUB('${biz_date}', [N-1]) 
  AND dt <= '${biz_date}'
GROUP BY [id_column_1];
*/

-- ----------------------------------------------------------------------------
-- STEP 2.6: STORAGE MAINTENANCE (OPTIMIZE / VACUUM)
-- ----------------------------------------------------------------------------

-- Compact small files for better read performance (Databricks)
-- Note: on Databricks native SQL, replace ${biz_date} with ${var:biz_date}
OPTIMIZE [catalog_name].[schema_name].[table_name]
WHERE processing_date = DATE('${biz_date}');

-- Z-Order indexing for multi-column filtering (Databricks / Spark 3.3+)
-- Prefer Liquid Clustering (CLUSTER BY) over ZORDER for new tables on Databricks 13.3+
OPTIMIZE [catalog_name].[schema_name].[table_name]
WHERE processing_date = DATE('${biz_date}')
ZORDER BY (business_key_1, metric_amt_1);

-- Remove old files (retention 7 days default, adjust for compliance)
-- VACUUM [catalog_name].[schema_name].[table_name] RETAIN 168 HOURS;

-- ----------------------------------------------------------------------------
-- STEP 2.7: DATA QUALITY CHECKS (POST-LOAD)
-- ----------------------------------------------------------------------------

-- Check 1: Verify record count
SELECT 
    'POST_LOAD_COUNT_CHECK' AS check_name,
    COUNT(*) AS row_count,
    COUNT(DISTINCT [id_column_1]) AS distinct_keys
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}';

-- Check 2: Verify no null primary keys
SELECT 
    'NULL_KEY_CHECK' AS check_name,
    COUNT(*) AS null_key_count
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}'
  AND [id_column_1] IS NULL;
-- Should return 0

-- Check 3: Verify no duplicate keys
SELECT 
    'DUPLICATE_KEY_CHECK' AS check_name,
    [id_column_1],
    COUNT(*) AS dup_count
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}'
GROUP BY [id_column_1]
HAVING COUNT(*) > 1;
-- Should return 0

-- Check 4: Verify metric bounds
SELECT 
    'METRIC_BOUNDS_CHECK' AS check_name,
    COUNT(*) AS negative_metric_count
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}'
  AND [metric_amt_1] < 0;
-- Should return 0

-- Check 5: Verify partition was loaded
SELECT 
    'PARTITION_CHECK' AS check_name,
    dt,
    COUNT(*) AS row_count
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}'
GROUP BY dt;
-- Should return exactly 1 row with the business date

-- ----------------------------------------------------------------------------
-- STEP 2.8: RECONCILIATION WITH SOURCE
-- ----------------------------------------------------------------------------

-- Compare source and target counts
SELECT 
    'source' AS layer,
    COUNT(*) AS row_count,
    SUM([metric_amt_1]) AS total_amount
FROM [source_table_name]
WHERE dt = '${biz_date}'
UNION ALL
SELECT 
    'target' AS layer,
    COUNT(*) AS row_count,
    SUM([metric_amt_1]) AS total_amount
FROM [layer]_[domain]_[entity]_[granularity]_[suffix]
WHERE dt = '${biz_date}';
-- Row counts and totals should match (or be within expected variance)

-- ----------------------------------------------------------------------------
-- STEP 2.9: LOG ETL EXECUTION
-- ----------------------------------------------------------------------------

INSERT INTO etl_job_execution_log (
    job_name,
    table_name,
    partition_dt,
    start_time,
    end_time,
    status,
    row_count,
    error_message,
    batch_id
) VALUES (
    '[JOB_NAME]',
    '[layer]_[domain]_[entity]_[granularity]_[suffix]',
    '${biz_date}',
    '[START_TIME]',
    CURRENT_TIMESTAMP(),
    '[SUCCESS/FAILED]',
    (SELECT COUNT(*) FROM [layer]_[domain]_[entity]_[granularity]_[suffix] WHERE dt = '${biz_date}'),
    '[ERROR_MESSAGE_IF_ANY]',
    '${batch_id}'
);

-- ============================================================================
-- END OF SQL TEMPLATE
-- ============================================================================