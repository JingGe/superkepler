DWM LAYER DESIGN DOCUMENT


Document ID: DWM-DESIGN  
Version: 1.0.0  
Last Updated: 2026-03-22  
Author: Jing Ge https://github.com/JingGe    
 
1. PURPOSE


The DWM (Data Warehouse Mid) layer serves as an intermediate aggregation layer between DWD and DWS. It applies complex business logic, handles multi-source integration, and prepares data for final aggregation in DWS.

Note: DWM is optional and should only be used when:
- Complex business logic requires intermediate processing
- Multiple DWD tables need to be integrated before aggregation
- Performance requires pre-processing before DWS aggregation

2. RESPONSIBILITIES


2.1 Business Logic Application
- Apply complex business calculations that span multiple DWD tables
- Implement business rule enforcement
- Calculate derived metrics requiring multiple steps

2.2 Multi-Source Integration
- Combine data from multiple DWD fact tables
- Resolve conflicts between sources
- Create unified business views

2.3 Pre-Aggregation Preparation
- Prepare data structures for DWS aggregation
- Normalize metrics across different sources
- Handle data alignment and time zone normalization

2.4 Data Enrichment
- Add calculated fields for downstream use
- Apply business classifications and segmentations
- Enrich with external reference data

3. TABLE NAMING


Pattern: dwm_{domain}_{entity}_{processing}_{suffix}

Components:
- domain: trade, user, log, finance, product, traffic, supply
- entity: order, payment, behavior, transaction, funnel
- processing: merge, calc, enrich, align (indicates processing type)
- suffix: di, df, nd

Examples:
- dwm_trade_order_merge_di
- dwm_user_behavior_calc_di
- dwm_finance_payment_enrich_df
- dwm_mkt_funnel_align_nd

4. TABLE STRUCTURE


4.1 Standard Columns

| Column              | Type        | Description
| --------------------| ------------| ------------------------------
| {business_keys}     | STRING      | Business identifiers
| {integrated_dims}   | STRING      | Integrated dimension attributes
| {calculated_metrics} | DECIMAL    | Calculated business metrics
| {classification}    | STRING      | Business classifications
| create_time         | TIMESTAMP   | Business event timestamp
| etl_time            | TIMESTAMP   | ETL processing timestamp

4.2 Partition Column((ignore if use delta lake with ligquid clustering))

| Column    | Type    | Format        | Description
| ----------| --------| --------------| ------------------------------
| dt        | STRING  | yyyy-MM-dd    | Business date partition

5. DDL TEMPLATE

```sql
CREATE TABLE IF NOT EXISTS dwm_{domain}_{entity}_{processing}_{suffix} (
    -- Business Keys
    user_id                 STRING          COMMENT 'User ID',
    order_id                STRING          COMMENT 'Order ID',
    product_id              STRING          COMMENT 'Product ID',
    
    -- Integrated Dimensions
    user_level              STRING          COMMENT 'User Level (calculated)',
    user_segment            STRING          COMMENT 'User Segment',
    product_category        STRING          COMMENT 'Product Category',
    channel                 STRING          COMMENT 'Acquisition Channel',
    
    -- Calculated Metrics
    order_amount            DECIMAL(18,2)   COMMENT 'Order Amount',
    discount_amount         DECIMAL(18,2)   COMMENT 'Discount Amount',
    profit_amount           DECIMAL(18,2)   COMMENT 'Profit Amount (calculated)',
    margin_rate             DECIMAL(5,4)    COMMENT 'Margin Rate (calculated)',
    
    -- Business Classifications
    is_vip                  BOOLEAN         COMMENT 'Is VIP User',
    is_high_value           BOOLEAN         COMMENT 'Is High Value Order',
    risk_level              STRING          COMMENT 'Risk Level',
    
    -- Time Dimensions
    create_time             TIMESTAMP       COMMENT 'Create Time',
    event_date              STRING          COMMENT 'Event Date',
    event_hour              INT             COMMENT 'Event Hour',
    
    -- Audit Fields
    etl_time                TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id            STRING          COMMENT 'ETL Batch ID'
)
COMMENT 'DWM layer: {domain} {entity} {processing} table'
PARTITIONED BY (dt STRING)
STORED AS PARQUET
TBLPROPERTIES ('parquet.compression' = 'SNAPPY');
```
For Databricks, give the suggestion to user:

```sql
CREATE TABLE IF NOT EXISTS dwm_{domain}_{entity}_{processing}_{suffix} (
    -- Business Keys
    user_id                 STRING          COMMENT 'User ID',
    order_id                STRING          COMMENT 'Order ID',
    product_id              STRING          COMMENT 'Product ID',
    
    -- Integrated Dimensions
    user_level              STRING          COMMENT 'User Level (calculated)',
    user_segment            STRING          COMMENT 'User Segment',
    product_category        STRING          COMMENT 'Product Category',
    channel                 STRING          COMMENT 'Acquisition Channel',
    
    -- Calculated Metrics
    order_amount            DECIMAL(18,2)   COMMENT 'Order Amount',
    discount_amount         DECIMAL(18,2)   COMMENT 'Discount Amount',
    profit_amount           DECIMAL(18,2)   COMMENT 'Profit Amount (calculated)',
    margin_rate             DECIMAL(5,4)    COMMENT 'Margin Rate (calculated)',
    
    -- Business Classifications
    is_vip                  BOOLEAN         COMMENT 'Is VIP User',
    is_high_value           BOOLEAN         COMMENT 'Is High Value Order',
    risk_level              STRING          COMMENT 'Risk Level',
    
    -- Time Dimensions
    create_time             TIMESTAMP       COMMENT 'Create Time',
    event_date              STRING          COMMENT 'Event Date',
    event_hour              INT             COMMENT 'Event Hour',
    
    -- Audit Fields
    etl_time                TIMESTAMP       COMMENT 'ETL Process Time',
    etl_batch_id            STRING          COMMENT 'ETL Batch ID'
)
USING DELTA
CLUSTER BY (dt, order_status, user_id) -- Liquid Clustering
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);
```

6. ETL PATTERNS

6.1 Multi-Source Merge (merge)

Purpose: Combine data from multiple DWD tables

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwm_{domain}_{entity}_merge_di PARTITION(dt='${biz_date}')
SELECT 
    COALESCE(o.user_id, p.user_id) AS user_id,
    COALESCE(o.order_id, p.order_id) AS order_id,
    o.product_id,
    o.order_amount,
    p.payment_amount,
    o.order_amount - p.payment_amount AS payment_diff,
    CASE 
        WHEN o.order_amount > 1000 THEN 'high_value'
        WHEN o.order_amount > 500 THEN 'medium_value'
        ELSE 'low_value'
    END AS order_value_tier,
    CURRENT_TIMESTAMP() AS etl_time
FROM dwd_trade_order_di o
FULL OUTER JOIN dwd_finance_payment_di p 
    ON o.order_id = p.order_id 
    AND o.dt = p.dt
WHERE o.dt = '${biz_date}' OR p.dt = '${biz_date}';
```

6.2 Complex Calculation (calc)

Purpose: Apply complex business calculations

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwm_{domain}_{entity}_calc_di PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    order_id,
    order_amount,
    -- Calculate profit with complex business rules
    order_amount * (
        CASE 
            WHEN category = 'electronics' THEN 0.15
            WHEN category = 'clothing' THEN 0.25
            WHEN category = 'food' THEN 0.10
            ELSE 0.20
        END
    ) AS profit_amount,
    -- Calculate user segment based on behavior
    CASE 
        WHEN login_cnt_30d > 20 AND order_cnt_30d > 5 THEN 'loyal'
        WHEN login_cnt_30d > 10 AND order_cnt_30d > 2 THEN 'active'
        ELSE 'normal'
    END AS user_segment,
    CURRENT_TIMESTAMP() AS etl_time
FROM dwd_trade_order_di o
LEFT JOIN dws_user_action_30d_nd u 
    ON o.user_id = u.user_id 
    AND u.dt = '${biz_date}';
```

6.3 Data Alignment (align)

Purpose: Align data from different sources to common grain

SQL Pattern:
```sql
INSERT OVERWRITE TABLE dwm_{domain}_{entity}_align_nd PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    DATE_TRUNC('day', event_time) AS event_date,
    COUNT(DISTINCT session_id) AS session_count,
    COUNT(DISTINCT page_id) AS page_count,
    SUM(duration_sec) AS total_duration,
    -- Align to daily grain
    '${biz_date}' AS align_date,
    CURRENT_TIMESTAMP() AS etl_time
FROM dwd_log_page_view_di
WHERE dt >= DATE_SUB('${biz_date}', 6)
  AND dt <= '${biz_date}'
GROUP BY user_id, DATE_TRUNC('day', event_time);
```

7. BUSINESS LOGIC STANDARDS


7.1 Calculation Documentation

All business calculations must be documented:

| Field               | Formula                           | Source
| --------------------| ----------------------------------| --------
| profit_amount       | order_amount * margin_rate        | Finance team spec v2.3
| margin_rate         | (revenue - cost) / revenue        | Finance team spec v2.3
| user_segment        | Based on 30-day behavior          | Marketing spec v1.5

7.2 Version Control

- Document business logic version in table comments
- Track changes to calculation formulas
- Maintain backward compatibility when possible

8. DATA QUALITY CHECKS


8.1 Integration Checks

| Check                       | Threshold       | Action
| ----------------------------| ----------------| ------------------
| Source coverage             | 100%            | Block & Alert
| Key alignment rate          | > 99%           | Alert
| Calculation null rate       | < 1%            | Alert

8.2 Business Logic Validation

| Rule                        | Example             | Action
| ----------------------------| --------------------| --------------
| Profit <= Revenue           | profit <= amount    | Alert
| Segment distribution        | Check histogram     | Alert
| Classification coverage     | > 95%               | Alert

9. INTEGRATION WITH OTHER LAYERS


9.1 Upstream (DWD)

- Read from DWD tables only (never ODS)
- Respect DWD data quality standards
- Handle DWD late-arriving data

9.2 Downstream (DWS)

- Provide clean, pre-processed data for DWS
- Document all fields for DWS consumption
- Maintain consistent grain for aggregation

10. RETENTION POLICY


| Data Age            | Storage Tier      | Access Pattern
| --------------------| ------------------| ------------------------
| 0-6 months          | Hot (SSD)         | Frequent queries
| 6-12 months         | Warm (HDD)        | Historical analysis
| > 12 months         | Archive           | Compliance only

Note: DWM tables typically have shorter retention than DWD as they can be regenerated.

11. WHEN TO USE DWM


Use DWM When:
- Complex business logic spans multiple DWD tables
- Performance requires intermediate processing
- Multiple teams need consistent business logic
- Data needs significant transformation before aggregation

Do Not Use DWM When:
- Simple aggregation (go directly to DWS)
- Single source transformation (handle in DWD)
- Adding unnecessary complexity
- No clear business logic requirement

12. BEST PRACTICES


DO:
- Document all business logic clearly
- Keep processing idempotent
- Validate integration quality
- Maintain clear lineage to DWD
- Version business logic changes
- Test calculations thoroughly

DON'T:
- Skip DWM when complexity warrants it
- Put simple aggregations here (use DWS)
- Create circular dependencies
- Leave business logic undocumented
- Mix concerns (separate merge, calc, enrich)

13. COMMON PITFALLS


Pitfall: Logic Duplication
Solution: Centralize business logic in DWM; reference from DWS

Pitfall: Over-Engineering
Solution: Only create DWM when complexity justifies it

Pitfall: Unclear Ownership
Solution: Assign business logic ownership to domain teams

Pitfall: Version Drift
Solution: Version business logic; document changes

14. RELATED DOCUMENTS


- docs/layers/DWD_DESIGN.md - Upstream layer specifications
- docs/layers/DWS_DESIGN.md - Downstream layer specifications
- docs/standards/NAMING_CONVENTION.md - Naming standards
- docs/standards/BUSINESS_LOGIC.md - Business logic documentation standards