# DWD LAYER DESIGN DOCUMENT

Document ID: DWD-DESIGN  
version: 1.2.0  
Last Updated: 2026-04-18  
Author: Jing Ge https://github.com/JingGe  

1. PURPOSE

The DWD (Data Warehouse Detail) layer transforms ODS data into clean, standardized, business-meaningful detail tables using dimensional modeling principles. This layer serves as the foundation for all downstream analytics. In the Lakehouse architecture, this layer sits at the Silver level, providing a reliable foundation for downstream DWS (Summary) and ADS (Application) layers.

2. RESPONSIBILITIES

2.1 Data Cleansing
- Remove dirty data and handle nulls according to business rules
- Validate business rules (e.g., filter orders with amount <= 0)
- Deduplicate records based on business keys using MERGE or Window functions
- Implement "Data Quality as Code" using Delta Live Tables (DLT) or Spark expectations.

2.2 Standardization
- Unify data formats, enums, and naming conventions
- Standardize currency(ISO 4217), timezone(UTC), and measurement units
- Apply consistent code mappings (e.g., gender, status codes)

2.3 Dimension Degeneration
- Embed frequently-used dimension attributes into fact tables
- Reduce join complexity for common queries
- Balance normalization with query performance

2.4 Business Logic Application
- Apply domain-specific transformations
- Calculate derived fields (e.g., order_status from multiple fields)
- Implement business rule validation

2.5 Sensitive Data Handling
- Mask PII for compliance (hash phone numbers, mask IDs)
- Apply row-level security markers where needed
- Document data classification levels

3. TABLE NAMING

Pattern: dwd_{domain}_{entity}_{suffix}

Components:
- domain: trade, user, log, finance, product, traffic, supply
- entity: order, payment, login, transaction, item, detail
- suffix: di, df, hi, stream

Examples:
- dwd_trade_order_di
- dwd_trade_order_detail_di
- dwd_user_login_di
- dwd_finance_payment_di
- dwd_log_page_view_di

4. TABLE STRUCTURE

4.1 Fact Table Types

| Type                    | Granularity         | Example                | Logic
| ------------------------| --------------------| -----------------------| ---------------------------------
| Transaction Fact        | One row per event   | dwd_trade_order_di     | Daily incremental load via INSERT OVERWRITE
| Periodic Snapshot       | One row per period  | dwd_inventory_daily_df | Daily FULL OUTER JOIN or state capture
| Accumulating Snapshot   | One row per process | dwd_order_lifecycle_df | Multi-step lifecycle updates via MERGE

4.2 Standard Columns

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| {business_keys}     | STRING      | Business identifiers
| {degenerated_dims}  | STRING      | Embedded dimension attributes
| {measures}          | DECIMAL     | Business metrics
| create_time         | TIMESTAMP   | Business event timestamp
| etl_time            | TIMESTAMP   | ETL processing timestamp

4.3 Partition Column(ignore if use delta lake with ligquid clustering)

| Column    | Type    | Format        | Description
| ----------| --------| --------------| ------------------------------
| dt        | STRING  | yyyy-MM-dd    | Business date partition

4.4 Storage Engine (Delta Lake)

All DWD tables should use the DELTA format in order to support ACID transactions, Time Travel, and Change Data Feed (CDF).


5. DDL TEMPLATE

```sql
CREATE TABLE IF NOT EXISTS dwd_{domain}_{entity}_{suffix} (
    -- Business Keys
    order_id              STRING          COMMENT 'Order ID (Business Key)',
    user_id               STRING          COMMENT 'User ID',
    product_id            STRING          COMMENT 'Product ID',
    
    -- Degenerated Dimensions
    product_name          STRING          COMMENT 'Product Name',
    category_l1           STRING          COMMENT 'Level 1 Category',
    category_l2           STRING          COMMENT 'Level 2 Category',
    shop_name             STRING          COMMENT 'Shop Name',
    
    -- Business Measures
    order_amount          DECIMAL(18,2)   COMMENT 'Order Amount',
    discount_amount       DECIMAL(18,2)   COMMENT 'Discount Amount',
    tax_amount            DECIMAL(18,2)   COMMENT 'Tax Amount',
    quantity              BIGINT          COMMENT 'Order Quantity',
    
    -- Time Dimensions
    create_time           TIMESTAMP       COMMENT 'Order Create Time',
    pay_time              TIMESTAMP       COMMENT 'Payment Time',
    ship_time             TIMESTAMP       COMMENT 'Shipping Time',
    
    -- Status & Flags
    order_status          STRING          COMMENT 'Order Status',
    is_paid               BOOLEAN         COMMENT 'Is Order Paid',
    is_refunded           BOOLEAN         COMMENT 'Is Order Refunded',
    
    -- Audit Fields
    etl_time              TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id          STRING          COMMENT 'ETL Batch ID'
)
COMMENT 'DWD layer: {domain} {entity} fact table'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
```

For Databricks, give the suggestion to user:

```sql
CREATE TABLE IF NOT EXISTS dwd_{domain}_{entity}_{suffix} (
    -- Business Keys
    order_id              STRING          COMMENT 'Order ID (Business Key)',
    user_id               STRING          COMMENT 'User ID',
    product_id            STRING          COMMENT 'Product ID',
    
    -- Degenerated Dimensions
    product_name          STRING          COMMENT 'Product Name',
    category_l1           STRING          COMMENT 'Level 1 Category',
    category_l2           STRING          COMMENT 'Level 2 Category',
    shop_name             STRING          COMMENT 'Shop Name',
    
    -- Business Measures
    order_amount          DECIMAL(18,2)   COMMENT 'Order Amount',
    discount_amount       DECIMAL(18,2)   COMMENT 'Discount Amount',
    tax_amount            DECIMAL(18,2)   COMMENT 'Tax Amount',
    quantity              BIGINT          COMMENT 'Order Quantity',
    
    -- Time Dimensions
    create_time           TIMESTAMP       COMMENT 'Order Create Time',
    pay_time              TIMESTAMP       COMMENT 'Payment Time',
    ship_time             TIMESTAMP       COMMENT 'Shipping Time',
    
    -- Status & Flags
    order_status          STRING          COMMENT 'Order Status',
    is_paid               BOOLEAN         COMMENT 'Is Order Paid',
    is_refunded           BOOLEAN         COMMENT 'Is Order Refunded',
    
    -- Audit Fields
    etl_time              TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id          STRING          COMMENT 'ETL Batch ID'
)
USING DELTA
CLUSTER BY (dt, order_status, user_id) -- Liquid Clustering
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);
```

6. ETL PATTERNS

6.1 Transaction Fact (di)

Purpose: Capture individual business events

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwd_{domain}_{entity}_di PARTITION(dt='${biz_date}')
SELECT 
    o.order_id,
    o.user_id,
    o.product_id,
    p.product_name,           -- Dimension degeneration
    c.category_l1,
    c.category_l2,
    o.amount - o.discount AS order_amount,
    o.discount AS discount_amount,
    o.create_time,
    o.pay_time,
    CASE WHEN o.pay_time IS NOT NULL THEN 'paid' ELSE 'unpaid' END AS order_status,
    CASE WHEN o.pay_time IS NOT NULL THEN TRUE ELSE FALSE END AS is_paid,
    CURRENT_TIMESTAMP() AS etl_time,
    '${batch_id}' AS etl_batch_id
FROM ods_{source}_orders o
LEFT JOIN dim_product p ON o.product_id = p.product_id AND p.is_current = TRUE
LEFT JOIN dim_category c ON p.category_id = c.category_id
WHERE o.dt = '${biz_date}'
  AND o.order_id IS NOT NULL
  AND o.amount > 0;
```

INSERT OVERWRITE is better than MERGE INTO for daily incremental fact table.

6.2 Periodic Snapshot Fact (df)

Purpose: Capture state at regular intervals

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwd_{domain}_{entity}_df PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    product_id,
    SUM(stock_quantity) AS stock_quantity,
    SUM(reserved_quantity) AS reserved_quantity,
    SUM(available_quantity) AS available_quantity,
    CURRENT_TIMESTAMP() AS etl_time
FROM ods_inventory_snapshot
WHERE dt = '${biz_date}'
GROUP BY user_id, product_id;
```

INSERT OVERWRITE is better than MERGE INTO for Periodic Snapshot fact table.

6.3 Accumulating Snapshot Fact

Purpose: Track progress through a process lifecycle(e.g., from Created to Paid to Shipped) without re-reading the whole history.

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwd_{domain}_{entity}_lifecycle_di PARTITION(dt='${biz_date}')
SELECT 
    order_id,
    user_id,
    product_id,
    create_time,
    MAX(CASE WHEN status = 'paid' THEN update_time END) AS pay_time,
    MAX(CASE WHEN status = 'shipped' THEN update_time END) AS ship_time,
    MAX(CASE WHEN status = 'delivered' THEN update_time END) AS deliver_time,
    CURRENT_TIMESTAMP() AS etl_time
FROM ods_order_status_log
WHERE dt <= '${biz_date}'
GROUP BY order_id, user_id, product_id, create_time;
```
For Databricks, give the suggestion to user:

```sql
MERGE INTO dwd_{domain}_{entity}_lifecycle_di AS target
USING (
  -- THIS SUBQUERY IS THE KEY
  -- It filters the SOURCE to only today's partition before the join
  SELECT * FROM ods_pg_order_status_di 
  WHERE dt = ${var.biz_date} 
    AND status IS NOT NULL
) AS source
ON target.order_id = source.order_id
-- If your target table is partitioned by 'dt', add it here for extra speed
-- AND target.dt = source.order_create_date 
WHEN MATCHED THEN
  UPDATE SET 
    target.pay_time = COALESCE(target.pay_time, CASE WHEN source.status = 'PAID' THEN source.event_time END),
    target.etl_updated_at = current_timestamp()
WHEN NOT MATCHED THEN
  INSERT (order_id, create_time, etl_inserted_at, dt) 
  VALUES (source.order_id, source.event_time, current_timestamp(), CAST(source.event_time AS DATE));
```

7. DIMENSION JOIN STRATEGY

7.1 Join Rules

- Always join to DIM tables with is_current = TRUE for current state
- When joining SCD Type 2 dimensions, ensure fact.event_time BETWEEN dim.start_time AND dim.end_time
- Use LEFT JOIN to preserve all fact records
- Use COALESCE(dim_col, 'Unknown') for orphan records
- Document all dimension joins in table comments

7.2 Dimension Degeneration Guidelines

Degenarate When:
- Attribute is frequently queried (> 80% of queries)
- Dimension table is small (< 1M rows)
- Attribute rarely changes (SCD Type 1)

Do Not Degenarate When:
- Attribute changes frequently (SCD Type 2 needed)
- Dimension table is large (> 10M rows). Create Bloom Filter Index to improve
- Attribute is rarely used in queries

For large dimension table (> 10M rows), create Bloom Filter Index for the fact table column to improve the join performance:

```sql
-- Delta Lake example
CREATE BLOOMFILTER INDEX ON TABLE dwd_trade_order
FOR COLUMNS (user_id OPTIONS (fpp=0.1, numItems=50000000));
```

8. DATA QUALITY CHECKS

8.1 Mandatory Checks

| Check                       | Threshold       | Action
| ----------------------------| ----------------| ------------------
| Null business keys          | 0%              | Block & Alert
| Negative measures           | 0%              | Block & Alert
| Orphan records (no dim)     | < 1%            | Alert
| Duplicate business keys     | 0%              | Block & Alert

8.2 Business Rule Validation

| Rule                        | Example                 | Action
| ----------------------------| ------------------------| --------------
| Amount > 0                  | order_amount > 0        | Filter & Log
| Valid status codes          | IN ('pending','paid')   | Filter & Log
| Date consistency            | pay_time >= create_time | Alert

9. SCD HANDLING IN DWD


9.1 Reference DIM with SCD

When joining to SCD Type 2 dimensions:
```sql
SELECT 
    f.order_id,
    d.user_name,
    d.city_code,
    d.start_date,
    d.end_date
FROM dwd_fact f
LEFT JOIN dim_user_his d 
    ON f.user_id = d.user_id 
    AND d.is_current = TRUE
    AND f.dt >= d.start_date 
    AND f.dt <= d.end_date;
```
9.2 Snapshot DIM Reference

For daily snapshot dimensions:
```sql
SELECT 
    f.order_id,
    d.user_name,
    d.city_code
FROM dwd_fact f
LEFT JOIN dim_user_df d 
    ON f.user_id = d.user_id 
    AND f.dt = d.dt;
```

10. RETENTION POLICY


| Data Age            | Storage Tier      | Access Pattern
| --------------------| ------------------| ------------------------
| 0-1 year            | Hot (SSD)         | Frequent queries
| 1-3 years           | Warm (HDD)        | Historical analysis
| > 3 years           | Archive           | Compliance only

11. MONITORING & ALERTING

11.1 Metrics to Track

- Record count per partition
- Join failure rate (orphan records)
- Data quality check pass rate
- ETL job duration
- Dimension coverage rate

11.2 Alert Thresholds

| Condition                       | Severity    | Notification
| --------------------------------| ------------| ------------------
| ETL job failure                 | Critical    | Page on-call
| Data quality check failure      | Critical    | Page on-call
| Orphan rate > 5%                | High        | Slack + Email
| Data volume deviation > 30%     | High        | Slack + Email

12. BEST PRACTICES

DO:
- Maintain atomic granularity (one row = one business event)
- Apply star schema modeling
- Document all transformation rules
- Use idempotent ETL jobs
- Handle NULLs with COALESCE
- Flatten dimensions as much as possible in the DWD
- Validate business rules before loading
- Enable Change Data Feed (CDF) to allow downstream DWS tables to process only changes.
- Run VACUUM and OPTIMIZE regularly to manage storage costs and performance.

DON'T:
- Aggregate in DWD (do in DWM/DWS)
- Create snowflake schemas and "deep" joins
- Leave logic undocumented
- Create non-reproducible jobs
- Skip dimension joins
- Store raw ODS data without cleaning

13. COMMON PITFALLS

Pitfall: Dimension Join Explosion  
Solution: Verify dimension cardinality before joining; use broadcast for small dims  

Pitfall: Late Arriving Dimensions  
Solution: Implement late-arriving dimension handling; allow reprocessing  

Pitfall: Inconsistent Business Logic  
Solution: Centralize business rules in documented SQL templates  

Pitfall: Data Skew on Join Keys  
Solution: Add salt to skewed keys; use skew join optimization  

14. Star Schema

See references/STAR_SCHEMA_DESIGN.md for grain and measure definitions.

15. RELATED DOCUMENTS

- references/ODS_DESIGN.md - Upstream ODS layer specifications
- references/DIM_DESIGN.md - Master data management, SCD Type 2 history tracking, and conformed dimension governance.
- references/DWM_DESIGN.md - Downstream DWM layer specifications
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards
- references/STAR_SCHEMA_DESIGN.md - Star schema design specification
