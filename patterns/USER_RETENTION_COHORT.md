# Cohort-Based User Retention Analysis Pattern

## Overview
This pattern provides an efficient incremental approach to calculating user retention by acquisition cohort. It avoids the exponential complexity of full historical recalculation (O(N²)) by incrementally processing only the daily active users, resulting in linear O(N) complexity.

## When to use this pattern
- You need to calculate user retention by acquisition cohort
- You have daily user activity events
- You want efficient incremental daily processing
- You need both relative-day and natural-week retention reporting

## Architecture

```mermaid
flowchart TD
    A[ods_{source}_user_events<br>ODS / Raw source] --> B[dwd_user_active_di<br>DWD / Cleaned filtered active events]
    B --> C[dim_user_profile_df<br>DIM / User profile with immutable first-active cohort]
    B --> D[dws_user_retention_matrix_1d_di<br>DWS / Incremental retention matrix]
    C --> D
    D --> E[v_ads_retention_matrix<br>ADS / Final presentation view]
```

## Key Design Principles
1. **Incremental Calculation (O(N) vs O(N²))**: Instead of joining all active users against all historical users (which grows exponentially), we only join today's active users against the user dimension. This results in linear growth: each day only processes today's activity.
2. **Broadcast Join Optimization**: The daily active user set is much smaller than the full user dimension. Spark/Photon automatically broadcast joins the small daily set against the user dimension, avoiding expensive shuffles.
3. **Immutable First-Active Data**: First-active cohort information is never changed once captured. This ensures consistent retention calculations over time, eliminating "retention drift".
4. **Idempotent Execution**: All daily steps use `INSERT INTO ... REPLACE WHERE dt = ...`. Safe to re-run for any date, enabling easy backfilling if source data is corrected.

## Table Naming & Layering

| Layer | Table Name | Type | Loading | Description |
|-------|------------|------|---------|-------------|
| ODS | `ods_{source}_user_events_<suffix>` | Fact | Source-dependent | Raw user events from source |
| DWD | `dwd_user_active_di` | Fact | di (daily incremental) | Cleaned filtered active user events |
| DIM | `dim_user_profile_df` | Dimension | df (daily full snapshot upsert) | User profile with immutable first-active cohort info |
| DWS | `dws_user_retention_matrix_1d_di` | Aggregate | di (daily incremental) | Incremental retention counts by cohort |
| ADS | `v_ads_retention_matrix` | View | N/A | Final view with calculated retention rates |

## Configuration
Before generating, confirm with user:
1. What source table contains the raw user events?
2. What event types count as "active" engagement? Filter these in DWD.
3. What lookback windows are needed for day and week retention? Default: 90 days / 26 weeks.
4. Does the user need to segment retention by additional attributes (channel is already included)? Add these to the dimension and grouping.

## SQL Templates

### ODS Table (`sql/ods/ods_raw_user_events.sql`)
```sql
-- ============================================================================
-- Table:       ods_{source}_user_events
-- Layer:       ODS
-- Source:      raw user events landing
-- Description: Raw user event data landing from source system
-- Platform:    Databricks
-- Pipeline:    DAB
-- Author:      {author}
-- Created:     {date}
-- ============================================================================
-- MODIFICATION HISTORY
-- {date} | {author} | Initial creation
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.ods_{source}_user_events (
    event_id            STRING          NOT NULL COMMENT 'Unique event identifier',
    user_id             STRING          NOT NULL COMMENT 'Unique user identifier',
    event_time          TIMESTAMP       COMMENT 'Timestamp when the event occurred',
    event_type          STRING          COMMENT 'Type of the user event',
    device_id           STRING          COMMENT 'Device identifier associated with the event',
    channel             STRING          COMMENT 'Marketing or acquisition channel',
    payload             STRING          COMMENT 'JSON payload containing additional event metadata',
    p_date              DATE            NOT NULL COMMENT 'Business date partition'
)
USING DELTA
PARTITIONED BY (p_date)
LOCATION '/mnt/delta/ods/ods_raw_user_events'
COMMENT 'ODS: Raw landing of user event data from source system'
TBLPROPERTIES (
    'delta.deletedVector.enabled' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);
```

### DWD Table (`sql/dwd/user/dwd_user_active_di.sql`)
```sql
-- ============================================================================
-- Table:       dwd_user_active_di
-- Layer:       DWD
-- Domain:      user
-- Description: Cleansed core active user engagement events for retention analysis
-- Platform:    Databricks
-- Pipeline:    DAB
-- Author:      {author}
-- Created:     {date}
-- ============================================================================
-- MODIFICATION HISTORY
-- {date} | {author} | Initial creation
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.dwd_user_active_di (
    user_id             STRING          NOT NULL COMMENT 'Unique user identifier',
    active_date         DATE            NOT NULL COMMENT 'Date extracted from event timestamp',
    active_timestamp    TIMESTAMP       COMMENT 'Original timestamp of the active event',
    channel             STRING          COMMENT 'User acquisition channel from event',
    event_type          STRING          COMMENT 'Type of engagement event (e.g. ai_chat, price_compare)',
    dt                  DATE            NOT NULL COMMENT 'Business date partition'
)
USING DELTA
PARTITIONED BY (dt)
CLUSTER BY (user_id, event_type)
COMMENT 'DWD: Cleansed daily incremental fact table of core user active engagement events'
TBLPROPERTIES (
    'delta.deletedVector.enabled' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- Create Bloom Filter Index to optimize large-scale join queries on user_id
CREATE BLOOMFILTER INDEX ON TABLE ${catalog}.${schema}.dwd_user_active_di
FOR COLUMNS (user_id OPTIONS (fpp=0.02, numItems=50000000));

-- Daily incremental ingestion
INSERT INTO ${catalog}.${schema}.dwd_user_active_di
REPLACE WHERE dt = '${exec_date}'
SELECT
    user_id,
    CAST(event_time AS DATE) AS active_date,
    event_time AS active_timestamp,
    COALESCE(channel, 'unknown') AS channel,
    event_type,
    CAST(event_time AS DATE) AS dt
FROM ${catalog}.${schema}.ods_{source}_user_events
WHERE p_date = '${exec_date}'
  AND user_id IS NOT NULL
  AND LENGTH(TRIM(user_id)) > 0
  AND event_type IN ('ai_chat', 'price_compare'); -- UPDATE: Filter for your core engagement events
```

### DIM Table (`sql/dim/dim_user_profile_df.sql`)
```sql
-- ============================================================================
-- Table:       dim_user_profile_df
-- Layer:       DIM
-- Domain:      user
-- Description: Conformed upsertable dimension table for user profile including first-active cohort info
-- Platform:    Databricks
-- Pipeline:    DAB
-- Author:      {author}
-- Created:     {date}
-- ============================================================================
-- MODIFICATION HISTORY
-- {date} | {author} | Initial creation
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.dim_user_profile_df (
    user_id                 STRING          NOT NULL COMMENT 'Unique user identifier (primary key)',
    first_active_timestamp  TIMESTAMP       COMMENT 'Timestamp of the user''s first ever event',
    first_active_date       DATE            COMMENT 'Date of the first activity',
    first_active_week       DATE            COMMENT 'Start date of the week (Monday) of first activity',
    first_active_month      DATE            COMMENT 'Start date of the month of first activity',
    first_channel           STRING          COMMENT 'Acquisition channel on first visit',
    updated_time            TIMESTAMP       COMMENT 'Last profile update timestamp',
    created_time            TIMESTAMP       COMMENT 'Record creation timestamp in warehouse'
)
USING DELTA
CLUSTER BY (user_id)
COMMENT 'DIM: Conformed daily full snapshot upsertable user profile dimension with first-active cohort info'
TBLPROPERTIES (
    'delta.deletedVector.enabled' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);
```

### DWS Table (`sql/dws/user/dws_user_retention_matrix_1d_di.sql`)
```sql
-- ============================================================================
-- Table:       dws_user_retention_matrix_1d_di
-- Layer:       DWS
-- Domain:      user
-- Description: Incremental daily retention matrix with relative day and natural week calculations
-- Platform:    Databricks
-- Pipeline:    DAB
-- Author:      {author}
-- Created:     {date}
-- ============================================================================
-- MODIFICATION HISTORY
-- {date} | {author} | Initial creation
-- ============================================================================

CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.dws_user_retention_matrix_1d_di (
    time_window_type        STRING          COMMENT 'Type of retention window: RELATIVE_DAY or NATURAL_WEEK',
    cohort_start_date       DATE            NOT NULL COMMENT 'Cohort initialization date or week start date',
    days_after              INT             COMMENT 'Elapsed days relative to cohort start (0, 1, 2...)',
    weeks_after             INT             COMMENT 'Elapsed weeks relative to cohort start (0, 1, 2...)',
    channel                 STRING          COMMENT 'User acquisition channel grouping',
    retained_users          BIGINT          COMMENT 'Number of retained users contributed by today''s active users',
    dt                      DATE            NOT NULL COMMENT 'Execution/Business processing date partition'
)
USING DELTA
PARTITIONED BY (dt)
CLUSTER BY (time_window_type, cohort_start_date)
COMMENT 'DWS: Daily incremental retention matrix with relative day and natural week retention calculations'
TBLPROPERTIES (
    'delta.deletedVector.enabled' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);

-- Incremental retention calculation
INSERT INTO ${catalog}.${schema}.dws_user_retention_matrix_1d_di
REPLACE WHERE dt = '${exec_date}'

-- 1. Relative Day Retention Calculation
SELECT
    'RELATIVE_DAY' AS time_window_type,
    f.first_active_date AS cohort_start_date,
    DATEDIFF(DAY, f.first_active_date, DATE '${exec_date}') AS days_after,
    NULL AS weeks_after,
    f.first_channel AS channel,
    COUNT(DISTINCT a.user_id) AS retained_users,
    DATE '${exec_date}' AS dt
FROM (
    -- Today's distinct active users (small footprint enables broadcast join)
    SELECT DISTINCT user_id
    FROM ${catalog}.${schema}.dwd_user_active_di
    WHERE dt = '${exec_date}'
      AND user_id IS NOT NULL
) a
LEFT JOIN ${catalog}.${schema}.dim_user_profile_df f ON a.user_id = f.user_id
WHERE f.first_active_date <= DATE '${exec_date}'
  AND f.first_active_date >= DATE_SUB(DATE '${exec_date}', 90) -- UPDATE: Adjust lookback window as needed
GROUP BY 1, 2, 3, 4, 5

UNION ALL

-- 2. Natural Week Retention Calculation
SELECT
    'NATURAL_WEEK' AS time_window_type,
    f.first_active_week AS cohort_start_date,
    NULL AS days_after,
    CAST(DATEDIFF(WEEK, f.first_active_week, DATE_TRUNC('WEEK', DATE '${exec_date}')) AS INT) AS weeks_after,
    f.first_channel AS channel,
    COUNT(DISTINCT a.user_id) AS retained_users,
    DATE '${exec_date}' AS dt
FROM (
    SELECT DISTINCT user_id
    FROM ${catalog}.${schema}.dwd_user_active_di
    WHERE dt = '${exec_date}'
      AND user_id IS NOT NULL
) a
LEFT JOIN ${catalog}.${schema}.dim_user_profile_df f ON a.user_id = f.user_id
WHERE f.first_active_week <= DATE_TRUNC('WEEK', DATE '${exec_date}')
  AND f.first_active_week >= DATE_SUB(DATE_TRUNC('WEEK', DATE '${exec_date}'), 26) -- UPDATE: Adjust lookback window as needed
GROUP BY 1, 2, 3, 4, 5;
```

### ADS View (`sql/ads/mkt/v_ads_retention_matrix.sql`)
```sql
-- ============================================================================
-- View:        v_ads_retention_matrix
-- Layer:       ADS
-- Domain:      mkt
-- Description: Final presentation view dynamically combining cohort size and retention counts
-- Platform:    Databricks
-- Pipeline:    DAB
-- Author:      {author}
-- Created:     {date}
-- ============================================================================
-- MODIFICATION HISTORY
-- {date} | {author} | Initial creation
-- ============================================================================

CREATE OR REPLACE VIEW ${catalog}.${schema}.v_ads_retention_matrix
COMMENT 'ADS: Ready-to-query retention matrix view with calculated retention rate percentages'
AS
WITH cohort_size_day AS (
    -- 1. Dynamically aggregate total initial cohort sizes (Day 0)
    SELECT
        first_active_date AS cohort_start_date,
        first_channel AS channel,
        COUNT(DISTINCT user_id) AS cohort_size
    FROM ${catalog}.${schema}.dim_user_profile_df
    GROUP BY 1, 2
),
cohort_size_week AS (
    -- 2. Dynamically aggregate total initial week cohort sizes (Week 0)
    SELECT
        first_active_week AS cohort_start_date,
        first_channel AS channel,
        COUNT(DISTINCT user_id) AS cohort_size
    FROM ${catalog}.${schema}.dim_user_profile_df
    GROUP BY 1, 2
)
-- Relative Day Retention Matrix
SELECT
    'RELATIVE_DAY' AS time_window_type,
    r.cohort_start_date,
    CONCAT('Day +', CAST(r.days_after AS STRING)) AS retention_period,
    r.days_after AS period_after,
    r.channel,
    c.cohort_size,
    r.retained_users,
    ROUND(CAST(r.retained_users AS DOUBLE) / NULLIF(c.cohort_size, 0) * 100, 2) AS retention_rate_pct
FROM (
    SELECT cohort_start_date, days_after, channel, SUM(retained_users) AS retained_users
    FROM ${catalog}.${schema}.dws_user_retention_matrix_1d_di
    WHERE time_window_type = 'RELATIVE_DAY'
    GROUP BY 1, 2, 3
) r
JOIN cohort_size_day c
  ON r.cohort_start_date = c.cohort_start_date
 AND r.channel = c.channel

UNION ALL

-- Natural Week Retention Matrix
SELECT
    'NATURAL_WEEK' AS time_window_type,
    r.cohort_start_date,
    CONCAT('Week +', CAST(r.weeks_after AS STRING)) AS retention_period,
    r.weeks_after AS period_after,
    r.channel,
    c.cohort_size,
    r.retained_users,
    ROUND(CAST(r.retained_users AS DOUBLE) / NULLIF(c.cohort_size, 0) * 100, 2) AS retention_rate_pct
FROM (
    SELECT cohort_start_date, weeks_after, channel, SUM(retained_users) AS retained_users
    FROM ${catalog}.${schema}.dws_user_retention_matrix_1d_di
    WHERE time_window_type = 'NATURAL_WEEK'
    GROUP BY 1, 2, 3
) r
JOIN cohort_size_week c
  ON r.cohort_start_date = c.cohort_start_date
 AND r.channel = c.channel;
```

## Pipeline Execution Order
1. **ODS**: Ingest raw user events for the day
2. **DWD**: Clean and filter to core active events
3. **DIM**: Upsert new users into user profile dimension (first-active data is immutable)
4. **DWS**: Calculate incremental retention contributions for today
5. **ADS**: Query the view for retention reports

## Customization Tips
- **Filter Events**: Adjust the `event_type IN (...)` filter in DWD to select your core engagement events that define "activity"
- **Lookback Windows**: Adjust the lookback constraints (default 90 days for day retention, 26 weeks for week retention) in DWS to match your reporting needs
- **Segmentation**: Extend the `dim_user_profile_df` table to add more user profile attributes that you may want to segment retention by (e.g., user segment, country, device type) and add those to the GROUP BY in both DWS and the ADS view
- **Extended Retention Tracking**: For longer retention tracking (e.g., 12 months), just increase the lookback window in DWS
