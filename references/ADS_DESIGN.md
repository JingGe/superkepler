ADS LAYER DESIGN DOCUMENT


Document ID: ADS-DESIGN  
Version: 1.0.2 
Last Updated: 2026-03-22  
Author: Jing Ge https://github.com/JingGe  

1. PURPOSE

The ADS (Application Data Service) layer delivers "Data Products." It provides highly aggregated, low-latency, and strictly governed datasets tailored for specific end-user applications: Executive Dashboards, Operational APIs, ML Feature Sets, and Regulatory Reporting.

2. RESPONSIBILITIES


2.1 Business Logic Finalization
- Apply final calculations and business rules
- Calculate complex derived metrics (YOY, MOM, growth rates)
- Implement business-specific filters and conditions

2.2 Application Formatting
- Structure data for target consumption format (JSON, flattened tables)
- Optimize schema for specific query patterns
- Prepare data for specific tools (BI, API, ML)

2.3 Performance Optimization
- Tune for low-latency query requirements
- Pre-sort, add indexes, use materialized views
- Optimize for specific storage engines (MySQL, ClickHouse, Redis)

2.4 Data Product Packaging
- Bundle related metrics into cohesive outputs
- Create "dashboard-ready" datasets
- Package data for specific consumers

2.5 Access Control Preparation
- Embed row/column-level security markers
- Add department/team filters
- Prepare for multi-tenant access patterns

2.6 Polyglot Persistence (Multi-Engine Delivery)

- Lakehouse Serving: High-speed SQL for BI (Databricks SQL/Serverless).
- Point-Lookup: Push to Redis or DynamoDB for millisecond API responses.
- OLAP Serving: Push to ClickHouse or StarRocks for sub-second interactive slicing.

2.7 Feature Engineering for ML

- Convert categorical data into one-hot encoding or embeddings for ML consumption.
- Maintain versioned snapshots for model training vs. inference.

2.8 Data Contract Enforcement

- Act as the boundary for Data Contracts. Any schema change in ADS requires a version bump and downstream notification.

3. TABLE NAMING


Pattern: ads_{app_name}_{metric}_{version}_{suffix}

Components:
- app_name: exec, mkt, crm, bi, finance, ops, ml
- metric: kpi, gmv, retention, label, report, dashboard
- suffix: df, di, rt(real-time), full, feat(ML Feature)

Examples:
- ads_exec_kpi_daily_df
- ads_mkt_campaign_result_di
- ads_crm_user_label_df
- ads_bi_order_analysis_df
- ads_ml_feature_daily_df
- ads_monitor_realtime_rt

4. TABLE STRUCTURE


4.1 Serving Architectures for Target Storage Engine

| Type            | Storage Engine    | Use Case
| ----------------| ------------------| ---------------------------------------------------------------------
| Lakehouse SQL	  | Databricks SQL	  | Internal BI (Tableau, PowerBI), Exploratory analysis.
| OLTP            | MySQL, PostgreSQL | Customer-facing portals, high-concurrency APIs.
| Real-time OLAP  | ClickHouse        | Analytics, Dashboards, Marketing Ops monitors, high-speed ad-hoc query.
| Key-Value       | Redis             | Caching, User Profile lookups, Real-time personalization.
| Document        | MongoDB           | Flexible schemas
| File            | Parquet, CSV      | Batch exports, ML

4.2 Standard Columns(Example)

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| {report_keys}       | STRING      | Report identifiers
| {kpi_metrics}       | DECIMAL     | Key performance indicators
| {growth_rates}      | DECIMAL     | Growth calculations (YOY, MOM)
| {rankings}          | INT         | Rank positions
| report_date         | DATE        | Report date
| etl_time            | TIMESTAMP   | ETL processing timestamp

4.3 Partition Column (if applicable)

| Column      | Type    | Format        | Description
| ------------| --------| --------------| ----------------------------
| dt          | STRING  | yyyy-MM-dd    | Business date partition
| report_date | DATE    | yyyy-MM-dd    | Report date

5. DDL TEMPLATE


5.1 Databricks SQL: The "Wide KPI" Table

A modern ADS table should include "Trend Metadata" so BI tools don't have to calculate it on the fly.

```sql
CREATE TABLE ads.exec.ads_exec_kpi_v1_df (
    report_date       DATE            NOT NULL,
    dim_region        STRING          COMMENT 'Hierarchy level 1',
    
    -- Metrics with built-in growth
    gmv_amt           DECIMAL(18,2)   COMMENT 'Current Day GMV',
    gmv_mom_growth    DECIMAL(7,4)    COMMENT 'Growth vs 30 days ago',
    gmv_yoy_growth    DECIMAL(7,4)    COMMENT 'Growth vs 365 days ago',
    
    -- Status Indicators (Dashboard-ready signals)
    gmv_health_flag   STRING          COMMENT 'Red/Yellow/Green status',
    
    -- Audit
    version_id        STRING,
    update_timestamp  TIMESTAMP       DEFAULT current_timestamp()
)
USING DELTA
CLUSTER BY (report_date, dim_region);
```

The dim_region hierarchy might look like this:

- Level 1 (Region): North America, EMEA, APAC.
- Level 2 (Country): USA, Canada, UK, Germany.
- Level 3 (State/Province): California, New York, Bavaria.
- Level 4 (City/Store): San Francisco, Munich.

5.1 MySQL (for API)

```sql
CREATE TABLE ads_exec_dashboard_daily (
    report_date          DATE            PRIMARY KEY,
    
    -- Core KPIs
    dau                  BIGINT          COMMENT 'Daily Active Users',
    new_users            BIGINT          COMMENT 'New Users',
    gmv                  DECIMAL(18,2)   COMMENT 'Gross Merchandise Value',
    order_count          BIGINT          COMMENT 'Order Count',
    
    -- Conversion Funnel
    browse_to_cart_rate  DECIMAL(5,4)    COMMENT 'Browse to Cart Conversion',
    cart_to_order_rate   DECIMAL(5,4)    COMMENT 'Cart to Order Conversion',
    order_to_payment_rate DECIMAL(5,4)   COMMENT 'Order to Payment Conversion',
    
    -- Growth Metrics
    dau_yoy_growth       DECIMAL(6,4)    COMMENT 'DAU Year-over-Year Growth',
    dau_mom_growth       DECIMAL(6,4)    COMMENT 'DAU Month-over-Month Growth',
    gmv_yoy_growth       DECIMAL(6,4)    COMMENT 'GMV Year-over-Year Growth',
    
    -- Audit Fields
    create_time          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    update_time          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_report_date (report_date)
) COMMENT 'ADS layer: Executive Dashboard Daily Metrics';
```

5.2 ClickHouse (for Analytics)

```sql
CREATE TABLE ads_bi_order_analysis_df (
    report_date          Date,
    category             String,
    order_count          UInt64,
    order_amount         Decimal(18,2),
    avg_order_value      Decimal(10,2),
    customer_count       UInt64,
    new_customer_count   UInt64,
    returning_customer_count UInt64,
    create_time          DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(report_date)
ORDER BY (report_date, category)
COMMENT 'ADS layer: BI Order Analysis';
```

6. ETL PATTERNS


6.1 Dashboard Aggregation (df)

Purpose: Full rebuild of dashboard metrics daily

SQL Pattern:

```sql
INSERT INTO ads_exec_dashboard_daily
SELECT 
    '${biz_date}' AS report_date,
    
    -- From DWS user table
    (SELECT COUNT(DISTINCT user_id) 
     FROM dws_user_action_1d_di 
     WHERE dt = '${biz_date}' AND login_cnt > 0) AS dau,
    
    (SELECT COUNT(*) 
     FROM dws_user_action_1d_di 
     WHERE dt = '${biz_date}' AND register_date = '${biz_date}') AS new_users,
    
    -- From DWS transaction table
    (SELECT SUM(pay_amt) 
     FROM dws_user_action_1d_di 
     WHERE dt = '${biz_date}') AS gmv,
    
    (SELECT SUM(order_cnt) 
     FROM dws_user_action_1d_di 
     WHERE dt = '${biz_date}') AS order_count,
    
    -- Funnel calculations
    (SELECT ROUND(SUM(CASE WHEN cart_add_cnt > 0 THEN 1 ELSE 0 END)*1.0 / COUNT(*), 4)
     FROM dws_user_action_1d_di 
     WHERE dt = '${biz_date}') AS browse_to_cart_rate,
    
    -- YOY growth (requires historical lookup)
    ROUND((dau_curr - dau_last_year)*1.0 / NULLIF(dau_last_year, 0), 4) AS dau_yoy_growth

FROM (
    SELECT 
        COUNT(DISTINCT CASE WHEN dt = '${biz_date}' THEN user_id END) AS dau_curr,
        COUNT(DISTINCT CASE WHEN dt = DATE_SUB('${biz_date}', INTERVAL 1 YEAR) THEN user_id END) AS dau_last_year
    FROM dws_user_action_1d_di
    WHERE dt IN ('${biz_date}', DATE_SUB('${biz_date}', INTERVAL 1 YEAR))
) t;
```

6.2 Incremental Report (di)

Purpose: Incremental update for report tables

SQL Pattern:

```sql
INSERT INTO ads_mkt_campaign_result_di
SELECT 
    campaign_id,
    '${biz_date}' AS report_date,
    SUM(impressions) AS impressions,
    SUM(clicks) AS clicks,
    SUM(conversions) AS conversions,
    SUM(cost) AS cost,
    SUM(revenue) AS revenue,
    ROUND(SUM(clicks)*1.0 / NULLIF(SUM(impressions), 0), 4) AS ctr,
    ROUND(SUM(conversions)*1.0 / NULLIF(SUM(clicks), 0), 4) AS cvr,
    ROUND(SUM(revenue) / NULLIF(SUM(cost), 0), 2) AS roas,
    CURRENT_TIMESTAMP() AS create_time
FROM dws_mkt_campaign_1d_di
WHERE dt = '${biz_date}'
GROUP BY campaign_id;
```

6.3 Real-Time Serving (rt)

Purpose: Low-latency data for real-time dashboards

SQL Pattern (Stream Processing):

```sql
INSERT INTO ads_monitor_realtime_rt
SELECT 
    window_start AS report_time,
    COUNT(DISTINCT user_id) AS dau,
    COUNT(DISTINCT order_id) AS order_count,
    SUM(order_amount) AS gmv,
    CURRENT_TIMESTAMP() AS create_time
FROM dwd_trade_order_rt
WHERE window_start >= NOW() - INTERVAL 5 MINUTE
GROUP BY window_start;
```
6.4 Growth Calculation

Purpose: Avoid subqueries for every metric. Use Window Functions (CET) for efficiency.

SQL Pattern(CET):

```sql
INSERT INTO ads_exec_kpi_v1_df
WITH daily_stats AS (
    SELECT 
        dt,
        SUM(pay_amt) as daily_gmv
    FROM dws_trade_1d_di
    WHERE dt >= DATE_SUB('${biz_date}', 400) -- Buffer for YOY
    GROUP BY dt
),
trends AS (
    SELECT 
        dt,
        daily_gmv,
        -- MOM: Current / (30 days ago) - 1
        LAG(daily_gmv, 30) OVER (ORDER BY dt) as gmv_30d_ago,
        -- YOY: Current / (364 days ago) - 1 (aligned by day of week)
        LAG(daily_gmv, 364) OVER (ORDER BY dt) as gmv_last_year
    FROM daily_stats
)
SELECT 
    dt as report_date,
    daily_gmv as gmv_amt,
    (daily_gmv - gmv_30d_ago) / NULLIF(gmv_30d_ago, 0) as gmv_mom_growth,
    (daily_gmv - gmv_last_year) / NULLIF(gmv_last_year, 0) as gmv_yoy_growth,
    CASE 
        WHEN (daily_gmv / NULLIF(gmv_30d_ago, 0)) < 0.8 THEN 'RED'
        ELSE 'GREEN' 
    END as gmv_health_flag
FROM trends
WHERE dt = '${biz_date}';
```

7. STORAGE ENGINE SELECTION


7.1 Selection Criteria

| Use Case            | Recommended Engine             | Reason
| --------------------| -------------------------------| -----------
| BI Dashboards       | Databricks SQL, ClickHouse     | Low latency, SQL support
| REST APIs           | MySQL, PostgreSQL              | Transaction support
| Real-time           | Redis, ClickHouse              | Low latency, high throughput
| ML Features         | Parquet, Feature Store         | Batch access, versioning
| Reports             | MySQL, Parquet                 | Export flexibility

7.2 Engine Configuration

MySQL:
- Use InnoDB engine
- Configure appropriate indexes
- Set up read replicas for scaling

ClickHouse:
- Use MergeTree family engines
- Configure partitioning by date
- Optimize ORDER BY keys

Redis:
- Use appropriate data structures (Hash, Sorted Set)
- Configure TTL for automatic expiration
- Set up persistence for durability

8. DATA QUALITY & SLA CHECKS

8.1 Data Quality

| Check                       | Requirement                         | Severity
| ----------------------------| ------------------------------------| ------------------
| Consistency                 | ads.gmv == dws.gmv                  | Critical (Stop Publishing)
| Freshness                   | T+1, T+h, or Real-time              | High (Alert Executive)
| Schema Change               | No column deletion or type change%  | Blocker (CI/CD Failure)

8.2 Business Logic Validation

| Check                       | Threshold       | Action
| ----------------------------| ----------------| ------------------
| KPI null rate               | 0%              | Block & Alert
| Growth rate bounds          | -99% to 1000%   | Alert
| Ranking consistency         | 100%            | Block & Alert

8.3 SLA Validation

| Metric                    | Target          | Action
| --------------------------| ----------------| --------------------
| Data freshness            | < 1 T           | Alert
| Report completeness       | 100%            | Block & Alert
| Query latency             | < 5 seconds     | Alert

9. ACCESS CONTROL


9.1 Row-Level Security

Add department/team filters:

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| dept_id             | STRING      | Department identifier
| team_id             | STRING      | Team identifier
| access_level        | STRING      | Access level (public, internal, confidential)

9.2 Column-Level Security

Mask sensitive columns:

| Column              | Masking Strategy
| --------------------| ------------------------------------------
| user_phone          | Hash or partial mask
| user_email          | Hash or partial mask
| revenue             | Aggregate only
| margin              | Restricted access

10. RETENTION POLICY


| Data Age            | Storage Tier      | Access Pattern
| --------------------| ------------------| ------------------------
| 0-3 months          | Hot (SSD)         | Active dashboards
| 3-6 months          | Warm (HDD)        | Historical reports
| > 6 months          | Archive           | Compliance only

Note: ADS tables typically have shorter retention as they can be regenerated from DWS.

11. MONITORING & ALERTING


11.1 Metrics to Track

- Data freshness (time since last update)
- Query latency (P50, P95, P99)
- Error rate (failed queries)
- Data completeness (expected vs actual)
- Consumer usage (query count by consumer)

11.2 SLA Definitions

| Report Type         | Freshness SLA   | Availability SLA
| --------------------| ----------------| --------------------------
| Executive Dashboard | < 1 hour        | 99.9%
| Operational Report  | < 4 hours       | 99.5%
| Analytical Report   | < 24 hours      | 99.0%
| Real-Time Monitor   | < 5 minutes     | 99.99%

11.3 Alert Thresholds

| Condition                       | Severity    | Notification
| --------------------------------| ------------| ------------------
| SLA breach                      | Critical    | Page on-call
| Data freshness > 2x SLA         | High        | Slack + Email
| Query error rate > 1%           | High        | Slack + Email
| Query latency > 10s             | Medium      | Email

12. BEST PRACTICES


DO:
- Optimize for target application
- Implement data freshness SLAs
- Version tables on logic changes
- Query from DWS only
- Document consumer requirements
- Test with production-like data

DON'T:
- Use generic warehouse format
- Allow stale data in dashboards
- Break downstream apps silently
- Bypass DWS to query DWD/ODS
- Skip access control
- Ignore query performance

13. COMMON PITFALLS
-------------------

Pitfall: Direct ODS Queries  
Solution: Enforce layer architecture; implement query routing  

Pitfall: Stale Data  
Solution: Implement freshness monitoring; alert on SLA breaches  

Pitfall: Breaking Changes  
Solution: Version ADS tables; maintain backward compatibility  

Pitfall: Performance Issues  
Solution: Profile queries; optimize indexes and schema  

Pitfall: Business Logic Leakage. Calculating the same "Active User" logic in three different ADS tables  
Solution: Move all logic to DWS; ADS only handles the formatting and time-shifting (YOY/MOM)  

Pitfall: PII Columns. Passing user_id to an external marketing API.  
Solution: ADS must use SHA-256 Hashing or Unity Catalog Masking before data leaves the Lakehouse.  

14. VERSIONING STRATEGY


14.1 Table Versioning

Format: ads_{app}_{metric}_{version}_{suffix}

Example:
- ads_exec_kpi_v1_daily_df (current)
- ads_exec_kpi_v2_daily_df (new version)

14.2 Deprecation Process

To prevent the "Broken Dashboard" syndrome, ADS employs a Blue-Green Deployment:

1. V-Next Development: Create ads_kpi_v2_df.
2. Parallel Run: Populate both v1 and v2 for 7 days.
3. Consumer Migration: Notify BI/API teams to switch endpoints. Mark old version as deprecated
4. V-Prev Sunset: Once v1 traffic hits zero in logs, drop or archive the table.


15. RELATED DOCUMENTS


- references/DWS_DESIGN.md - Upstream DWS layer specifications
- references/DIM_DESIGN.md - Master data management, SCD Type 2 history tracking, and conformed dimension governance.
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards