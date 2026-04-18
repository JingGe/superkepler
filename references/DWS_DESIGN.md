# DWS LAYER DESIGN DOCUMENT


Document ID: DWS-DESIGN  
version: 1.2.0  
Last Updated: 2026-04-18  
Author: Jing Ge https://github.com/JingGe    

1. PURPOSE


The DWS (Data Warehouse Service) layer provides pre-aggregated, topic-oriented wide tables to accelerate common analytical queries and ensure metric consistency across the organization. This layer serves as the "Single Source of Truth" for all KPI reporting.

2. RESPONSIBILITIES


2.1 Lightweight Aggregation
- Roll up DWD/DWM data by common dimensions (user, product, time)
- Pre-compute frequently used metrics
- Balance aggregation granularity for flexibility vs performance

2.2 Wide Table Construction
- Merge multiple related metrics into unified topic tables
- Create domain-area focused tables (user, product, trade, etc.)
- Reduce join complexity for common queries

2.3 Metric Standardization
- Define and enforce consistent business metric calculations
- Document metric definitions centrally
- Ensure same KPI calculated identically across reports

2.4 Time Window Aggregation
- Pre-compute common time-based metrics (1d, 7d, 30d, 90d)
- Support rolling window calculations
- Enable trend analysis without re-aggregation
- Performance optimization: Use Roaring Bitmaps for flexible "Count Distinct" (UV) calculations across any time range.

2.5 Cross-Domain Integration
- Combine data from multiple business processes
- Create unified views (e.g., user behavior + transactions)
- Enable cross-functional analysis

3. TABLE NAMING


Pattern: dws_{domain}_{entity}_{granularity}_{suffix}

Components:
- domain: user, trade, shop, product, traffic, finance, supply
- entity: action, order, sales, behavior, performance, stats
- granularity: 1d, 7d, 30d, 90d, nd (N-day rolling)
- suffix: di (from DWD), nd (rolling from 1d)

Examples:
- dws_user_click_1d_di
- dws_user_click_7d_nd
- dws_user_click_30d_nd
- dws_trade_order_1d_di
- dws_product_sales_7d_nd

4. TABLE STRUCTURE & Storage


4.1 Aggregation Levels

To avoid redundant I/O, Rolling Window tables (7d, 30d) should be built by aggregating the 1d DWS tables rather than re-scanning the raw DWD facts.

| Level               | Granularity         | Example
| --------------------| --------------------| ----------------------
| 1-Day (1d)          | Calendar day        | Activity ON specific date
| 7-Day (7d)          | Rolling 7 days      | Activity in [dt-6, dt]
| 30-Day (30d)        | Rolling 30 days     | Activity in [dt-29, dt]
| 90-Day (90d)        | Rolling 90 days     | Activity in [dt-89, dt]
| N-Day (nd)          | Generic rolling     | Configurable window

4.2 Standard Columns

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| {dimension_keys}    | STRING      | Aggregation dimensions
| {metric_cnt}        | BIGINT      | Count metrics (_cnt suffix)
| {metric_amt}        | DECIMAL     | Amount metrics (_amt suffix)
| {metric_rate}       | DECIMAL     | Rate metrics (_rate suffix)
| {last_time}         | STRING      | Last occurrence timestamps
| {first_time}        | STRING      | First occurrence timestamps

4.3 Partition Column(ignore if use delta lake with ligquid clustering)

| Column    | Type    | Format        | Description
| ----------| --------| --------------| ------------------------------
| dt        | STRING  | yyyy-MM-dd    | Business date partition

4.4 Storage Engine (Delta Lake)

- Format: USING DELTA.
- Clustering: Use CLUSTER BY (dt, user_id) (or shop_id). This co-locates a single entity's history across different days into the same physical files.

5. DDL TEMPLATE

```sql
CREATE TABLE IF NOT EXISTS dws_{domain}_{entity}_{granularity}_{suffix} (
    -- Dimension Keys
    user_id                 STRING          COMMENT 'User ID',
    
    -- Traffic Metrics
    login_cnt               BIGINT          COMMENT 'Login Count',
    pv_cnt                  BIGINT          COMMENT 'Page View Count',
    visit_cnt               BIGINT          COMMENT 'Session/Visit Count',
    duration_sec            BIGINT          COMMENT 'Total Duration (seconds)',
    
    -- Transaction Metrics
    order_cnt               BIGINT          COMMENT 'Order Count',
    order_amt               DECIMAL(18,2)   COMMENT 'Order Amount',
    pay_cnt                 BIGINT          COMMENT 'Payment Count',
    pay_amt                 DECIMAL(18,2)   COMMENT 'Payment Amount',
    refund_cnt              BIGINT          COMMENT 'Refund Count',
    refund_amt              DECIMAL(18,2)   COMMENT 'Refund Amount',
    
    -- Behavior Metrics
    cart_add_cnt            BIGINT          COMMENT 'Add to Cart Count',
    fav_cnt                 BIGINT          COMMENT 'Favorite Count',
    coupon_use_cnt          BIGINT          COMMENT 'Coupons Used',
    
    -- Derived Metrics
    avg_order_value         DECIMAL(10,2)   COMMENT 'Average Order Value',
    payment_conversion_rate DECIMAL(5,4)    COMMENT 'Payment Conversion Rate',
    days_active             BIGINT          COMMENT 'Number of Active Days',
    
    -- Time Markers
    last_login_time         STRING          COMMENT 'Last Login Timestamp',
    last_pay_time           STRING          COMMENT 'Last Payment Timestamp',
    first_order_time        STRING          COMMENT 'First Order Timestamp',
    
    -- Audit Fields
    etl_time                TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id            STRING          COMMENT 'ETL Batch ID'
)
COMMENT 'DWS layer: {domain} {entity} {granularity} summary table'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
```

6. ETL PATTERNS

6.1 1-Day Aggregation (from DWD)

Purpose: Aggregate DWD facts to daily grain per dimension

SQL Pattern:

```sql
INSERT OVERWRITE TABLE dws_user_action_1d_di PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    -- Traffic Metrics
    SUM(login_cnt) AS login_cnt,
    SUM(pv_cnt) AS pv_cnt,
    SUM(visit_cnt) AS visit_cnt,
    SUM(duration_sec) AS duration_sec,
    -- Transaction Metrics
    SUM(order_cnt) AS order_cnt,
    SUM(order_amt) AS order_amt,
    SUM(pay_cnt) AS pay_cnt,
    SUM(pay_amt) AS pay_amt,
    -- Derived Metrics
    ROUND(SUM(pay_amt) / NULLIF(SUM(pay_cnt), 0), 2) AS avg_order_value,
    ROUND(SUM(pay_cnt)*1.0 / NULLIF(SUM(order_cnt), 0), 4) AS payment_conversion_rate,
    COUNT(1) AS days_active,
    -- Time Markers
    MAX(login_time) AS last_login_time,
    MAX(pay_time) AS last_pay_time,
    MIN(order_time) AS first_order_time,
    CURRENT_TIMESTAMP() AS etl_time,
    '${batch_id}' AS etl_batch_id
FROM dwd_trade_order_di
WHERE dt = '${biz_date}'
  AND user_id IS NOT NULL
GROUP BY user_id;
```

6.2 Rolling 7-Day Aggregation (from 1d)

Purpose: Aggregate 1d tables to rolling 7-day window

SQL Pattern:

```sql
INSERT OVERWRITE TABLE dws_user_action_7d_nd PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    SUM(login_cnt) AS login_cnt_7d,
    SUM(pv_cnt) AS pv_cnt_7d,
    SUM(visit_cnt) AS visit_cnt_7d,
    SUM(duration_sec) AS duration_sec_7d,
    SUM(order_cnt) AS order_cnt_7d,
    SUM(order_amt) AS order_amt_7d,
    SUM(pay_cnt) AS pay_cnt_7d,
    SUM(pay_amt) AS pay_amt_7d,
    ROUND(SUM(pay_amt) / NULLIF(SUM(pay_cnt), 0), 2) AS avg_order_value_7d,
    COUNT(1) AS days_active_7d,
    MAX(last_login_time) AS last_login_time_7d,
    MAX(last_pay_time) AS last_pay_time_7d,
    CURRENT_TIMESTAMP() AS etl_time,
    '${batch_id}' AS etl_batch_id
FROM dws_user_action_1d_di
WHERE dt >= DATE_SUB('${biz_date}', 6) 
  AND dt <= '${biz_date}'
GROUP BY user_id;
```

6.3 Rolling 30-Day Aggregation (from 1d)

Purpose: Aggregate 1d tables to rolling 30-day window

SQL Pattern:

```sql
INSERT OVERWRITE TABLE dws_user_action_30d_nd PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    SUM(login_cnt) AS login_cnt_30d,
    SUM(pv_cnt) AS pv_cnt_30d,
    SUM(order_cnt) AS order_cnt_30d,
    SUM(pay_amt) AS pay_amt_30d,
    SUM(refund_amt) AS refund_amt_30d,
    SUM(pay_amt) - SUM(refund_amt) AS net_gmv_30d,
    COUNT(1) AS days_active_30d,
    CASE WHEN MAX(dt) < DATE_SUB('${biz_date}', 7) THEN 1 ELSE 0 END AS is_churn_risk,
    CURRENT_TIMESTAMP() AS etl_time,
    '${batch_id}' AS etl_batch_id
FROM dws_user_action_1d_di
WHERE dt >= DATE_SUB('${biz_date}', 29) 
  AND dt <= '${biz_date}'
GROUP BY user_id;
```

6.4 Storage optimization with Databricks: Liquid Clustering

For Databricks, give the suggestion to replace PARTITION(dt) with USING DELTA CLUSTER BY (dt, user_id)

6.5 7d/30d/90d rolling windows optimization

Give suggestion that, for the 7d/30d/90d rolling windows, do not build them all on day one.

- Start with the 1d table.
- Create Materialized Views in Databricks for the 7d and 30d logic.
- Only "physicalize" them into a DWS table if the Materialized View is too slow for the BI dashboard. This saves massive amounts of compute and storage.

6.6 SQL Performance optimization with Databricks

Give skill-users the following suggestions if Databricks is used and performance improvement is required. 

Instead of a traditional GROUP BY which re-reads the entire 30-day window from scratch every day, skill-users could use a High-Water Mark (Bitmaps) for user counts and a Delta Change Data Feed (CDF) style logic for sums. This ensures the DWS layer stays fast even with millions of user entries.

skill-users could use Roaring Bitmaps for "Days Active" to allow for any-window calculation (e.g., if someone suddenly asks for a 14-day window, you don't need a new table).

In the upgraded DDL, skill-users could replace the granular user_id with a user_id_bitmap column. Note that Bitmaps in Databricks/Spark are stored as BINARY and typically organized by a bucket_id.

In the upgraded INSERT logic, skill-users cloud use bitmap_bucket_number to group IDs and bitmap_construct_aggregate to compress them.

Show skill-users the example SQL and ask them to refer to Databricks official document.

7. METRIC STANDARDIZATION


7.1 Metric Definitions

All metrics must be defined in central catalog:

| Metric                  | Definition                          | Formula
| ------------------------| ------------------------------------| -------------------------------------------
| GMV                     | Gross Merchandise Value             | SUM(paid_order_amount)
| DAU                     | Daily Active Users                  | COUNT(DISTINCT user_id WHERE login_cnt > 0)
| Conversion Rate         | Order to Payment Conversion         | pay_cnt / order_cnt
| AOV                     | Average Order Value                 | pay_amt / pay_cnt
| Retention Rate          | Day-N Retention                     | RETURNING_USERS / NEW_USERS

7.2 Metric Naming

| Suffix      | Type            | Example
| ------------| ----------------| ----------------------------------
| _cnt        | Count           | login_cnt, order_cnt
| _amt        | Amount          | order_amt, pay_amt
| _rate       | Rate            | conversion_rate, retention_rate
| _avg        | Average         | avg_order_value
| _max        | Maximum         | max_order_amount
| _min        | Minimum         | min_order_amount

8. DATA QUALITY CHECKS


8.1 Aggregation Checks

| Check                       | Threshold       | Action
| ----------------------------| ----------------| ------------------
| Metric null rate            | < 1%            | Alert
| Sum consistency (1d vs 7d)  | +/- 1%          | Alert
| User count deviation        | +/- 10%         | Alert

8.2 Business Logic Validation

| Rule                        | Example             | Action
| ----------------------------| --------------------| --------------
| Rates between 0-1           | 0 <= rate <= 1      | Alert
| Counts non-negative         | cnt >= 0            | Block
| Amounts non-negative        | amt >= 0            | Block

9. PERFORMANCE OPTIMIZATION


9.1 File Management

- Target file size: 128MB - 1GB
- Enable file compaction after ETL
- Monitor small file count

9.2 Partition Management

- Partition by dt for all time-series DWS tables
- Consider secondary partitioning for large tables
- Archive old partitions per retention policy
- For Delta Lake, use liquid clustering instead, i.e. USING DELTA CLUSTER BY (dt, user_id)

9.3 Query Optimization

- Create frequently accessed subsets as separate tables
- Consider materialized views for common queries
- Document recommended query patterns

10. RETENTION POLICY


| Data Age            | Storage Tier      | Access Pattern
| --------------------| ------------------| ------------------------
| 0-6 months          | Hot (SSD)         | Frequent queries
| 6-12 months         | Warm (HDD)        | Historical analysis
| > 12 months         | Archive           | Aggregate to monthly

- Hot Data (0-90 Days): Keep in Delta Lake with Liquid Clustering.
- Cold Data (> 90 Days): Aggregate to dws_{domain}_{entity}_1month_di and archive daily details to cheap storage (S3 Glacier/Azure Archive).

11. MONITORING & ALERTING


11.1 Metrics to Track

- Record count per partition
- Aggregation completeness
- Metric consistency across windows
- ETL job duration
- Query performance

11.2 Alert Thresholds

| Condition                       | Severity    | Notification
| --------------------------------| ------------| ------------------
| ETL job failure                 | Critical    | Page on-call
| Metric inconsistency > 5%       | High        | Slack + Email
| Data volume deviation > 30%     | High        | Slack + Email
| Query latency > 30s             | Medium      | Email

12. BEST PRACTICES

DO:
- Design for 80% of common queries
- Document metric definitions centrally
- Build from DWD/DWM, not ODS
- Use incremental updates where possible
- Maintain consistent granularity
- Test aggregation logic thoroughly

DON'T:
- Over-aggregate (lose flexibility)
- Calculate metrics differently across tables
- Skip layers for "performance"
- Recompute everything from scratch
- Store raw data (use DWD for that)
- Mix granularities in one table

13. COMMON PITFALLS


Pitfall: Metric Inconsistency  
Solution: Centralize metric definitions; validate across tables  

Pitfall: Over-Aggregation  
Solution: Preserve necessary dimensions; document aggregation boundaries  

Pitfall: Performance Degradation  
Solution: Monitor file sizes; implement compaction  

Pitfall: Window Calculation Errors  
Solution: Test boundary conditions; document window definitions  

14. RELATED DOCUMENTS


- references/DWD_DESIGN.md - Upstream DWD layer specifications
- references/DWM_DESIGN.md - Upstream DWM layer specifications
- references/DIM_DESIGN.md - Master data management, SCD Type 2 history tracking, and conformed dimension governance.
- references/ADS_DESIGN.md - Downstream ADS layer specifications
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards  

