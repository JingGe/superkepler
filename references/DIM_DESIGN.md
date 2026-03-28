DIM LAYER DESIGN DOCUMENT


Document ID: DIM-DESIGN   
Version: 1.0.2   
Last Updated: 2026-03-23   
Author: Jing Ge https://github.com/JingGe    
 
1. PURPOSE & SCOPE


The DIM (Dimension) layer provides conformed dimensions that serve as the standardized descriptive attributes (who, what, where) used to filter and group facts in the DWD, DWS, and ADS layers.

Scope:
- Master data management for core business entities (User, Product, Shop, Category, etc.).
- Slowly Changing Dimension (SCD) strategy implementation. Provide "Point-in-Time" analysis via SCD Type 2.
- Conformed dimension governance across domains. One "User ID" means the same thing in Finance as it does in Marketing.
- Reference data and lookup tables.
- Denormalize snowflake schemas into flat wide-dimensions to reduce join depth.

Out of Scope:
- Transactional fact data (handled in DWD/DWS)
- Raw source ingestion (handled in ODS)
- Application-specific aggregations (handled in ADS)

2. DIMENSION TYPES


2.1 Conformed vs. Local Dimensions

| Type                | Definition                          | Example
| --------------------| ------------------------------------| -------------------------------------------
| Conformed           | Shared across multiple fact tables  | dim_user_info (used by trade, mkt, finance)
| Local               | Specific to one domain or use case  | dim_mkt_campaign_attr (marketing only)

Rule: Default to conformed. Create local dimensions only with architecture approval.

2.2 Transactional vs. Reference Dimensions

| Type           | Definition                      | Example                                | Strategy
| ---------------| --------------------------------| ---------------------------------------| ---------------------
| Transactional  | Changes with business events    | dim_user_info (user profile updates)   | SCD Type 2
| Reference      | Static or rarely changes        | dim_country_code, dim_currency         | SCD Type 1 / Full Overwrite
| Junk	         | Collection of flags/booleans	   | dim_order_flags	                    | Cross-join unique combinations

Rule: Reference dimensions can use simpler loading strategies (full load, no SCD).

2.3 Static vs. Dynamic Dimensions

| Type                | Definition                          | Update Pattern
| --------------------| ------------------------------------| ----------------------------------
| Static              | Pre-defined, rarely changes         | dim_date_info (generated once)
| Dynamic             | Populated from source systems       | dim_product_detail (synced daily)

3. TABLE NAMING


Pattern: dim_{entity}_{suffix}

Components:
- entity: order, payment, behavior, transaction, funnel
- suffix: df(Daily Full snapshot, standard for Reference data), scd2(History-tracking table), zip(Zipped/History-mapped table)

Examples:
- dim_user_info_
- dim_country_code 
- dim_currency

3. SCD STRATEGIES


3.1 SCD Type 1: Overwrite

Purpose: Replace old value with new value; no history tracking.

Use When:
- Attribute corrections (typos, data fixes)
- Non-analytical attributes (phone, email for contact)
- High-cardinality attributes where history is not needed

Implementation:
```sql
UPDATE dim_user_info
SET 
    user_name = '${new_name}',
    update_time = CURRENT_TIMESTAMP()
WHERE user_id = '${user_id}'
  AND is_current = TRUE;
```

TABLE STRUCTURE (TYPE 1):
| Column          | Type        | Description
| ----------------| ------------| --------------------------------------------------
| user_id         | STRING      | Natural key (business identifier)
| user_name       | STRING      | Current name (overwritten on change)
| city_code       | STRING      | Current city (overwritten on change)
| is_current      | BOOLEAN     | Always TRUE for Type 1
| update_time     | TIMESTAMP   | Last modification time

3.2 SCD Type 2: Add Row (History Tracking)

PURPOSE: Preserve history by adding new row for each change.

USE WHEN:
- Analytical attributes affecting reporting (city, category, segment)
- Compliance requirements for audit trail
- Trend analysis requiring historical context

IMPLEMENTATION:
```sql
-- Step 1: Close existing record
UPDATE dim_user_info
SET 
    end_date = DATE_SUB('${biz_date}', 1),
    is_current = FALSE
WHERE user_id = '${user_id}'
  AND is_current = TRUE
  AND city_code != '${new_city}';

-- Step 2: Insert new record
INSERT INTO dim_user_info
SELECT 
    user_id,
    user_name,
    '${new_city}' AS city_code,
    '${biz_date}' AS start_date,
    '9999-12-31' AS end_date,
    TRUE AS is_current,
    CURRENT_TIMESTAMP() AS update_time
FROM ods_user_info
WHERE user_id = '${user_id}'
  AND dt = '${biz_date}';
```

TABLE STRUCTURE (TYPE 2):
| Column          | Type        | Description
| ----------------| ------------| --------------------------------------------------
| user_id         | STRING      | Natural key
| user_name       | STRING      | Attribute value for this period
| city_code       | STRING      | Attribute value for this period
| start_date      | STRING      | Effective start date (yyyy-MM-dd)
| end_date        | STRING      | Effective end date (9999-12-31 for current)
| is_current      | BOOLEAN     | Flag for latest version
| version_id      | BIGINT      | Sequential version number

3.3 SCD Type 3: Add Column

PURPOSE: Track immediate previous value only.

USE WHEN:
- Need to compare current vs. previous value
- Limited history requirement
- Storage constraints prevent full Type 2

IMPLEMENTATION:
```sql
UPDATE dim_user_info
SET 
    city_code = '${new_city}',
    prev_city_code = city_code,
    update_time = CURRENT_TIMESTAMP()
WHERE user_id = '${user_id}';
```

TABLE STRUCTURE (TYPE 3):
| Column          | Type        | Description
| ----------------| ------------| --------------------------------------------------
| user_id         | STRING      | Natural key
| city_code       | STRING      | Current value
| prev_city_code  | STRING      | Previous value
| change_time     | TIMESTAMP   | When last change occurred

3.4 Hybrid SCD Strategy

Apply different SCD types to different attributes in the same table:

| Attribute       | SCD Type    | Reason
| ----------------| ------------| --------------------------------------------------
| user_name       | Type 1      | Display only, no analytical impact
| city_code       | Type 2      | Critical for regional analysis
| user_level      | Type 2      | Affects segmentation reports
| phone           | Type 1      | Contact info, corrections only


4. NAMING & STRUCTURE STANDARDS


4.1 Table Naming

PATTERN: dim_{domain}_{entity}_{suffix}

COMPONENTS:
- domain: user, product, shop, geo, finance, mkt, supply
- entity: info, detail, category, region, type, status
- suffix: df(Daily Full snapshot, standard for Reference data), full (static), scd2(History-tracking table), zip(Zipped/History-mapped table)


EXAMPLES:
- dim_user_info_df
- dim_product_detail_df
- dim_geo_region_full
- dim_order_status_full

4.2 Column Naming

PREFIX RULES:
- Natural key: {entity}_id (user_id, product_id)
- Surrogate key: {entity}_sk (user_sk, product_sk) - optional
- Attributes: descriptive lowercase (city_code, category_name)
- SCD control: start_date, end_date, is_current, version_id
- Audit: etl_create_time, etl_update_time, etl_batch_id

SUFFIX RULES:
- _id: Business/Natural Key
- _sk: Surrogate Key
- _code: Enumerated code
- _name: Human-readable label
- _desc: Description text
- _flag: Boolean indicator

4.3 Key Strategy

| Approach          | When to Use                     | Example
| ------------------| --------------------------------| ----------------------------
| Natural Key Only  | Small dimensions, stable keys   | dim_date_info
| Surrogate Key     | Large dimensions, changing keys | dim_user_info
| Hybrid            | Most common                     | Natural key for business, surrogate for joins

SURROGATE KEY GENERATION:
-- Option 1: Sequence
ROW_NUMBER() OVER (ORDER BY user_id) AS user_sk

-- Option 2: Hash (for distributed systems)
CAST(SHA2(user_id, 256) AS BIGINT) AS user_sk

-- Option 3: UUID (for global uniqueness)
UUID() AS user_sk

4.4 Audit Columns

All dimension tables must include:

| Column              | Type        | Description
| --------------------| ------------| ----------------------------------------------
| etl_create_time     | TIMESTAMP   | When record was first inserted
| etl_update_time     | TIMESTAMP   | When record was last modified
| etl_batch_id        | STRING      | ETL job identifier for lineage
| etl_source_system   | STRING      | Origin system identifier


5. HIERARCHY DESIGN


5.1 Hierarchy Patterns

| Pattern             | Structure Example           | Use Case
| --------------------| ----------------------------| ------------------------------
| Parent-Child        | parent_id, level_num        | Org charts, categories
| Path Enumeration    | l1_code, l2_code, l3_code   | Product taxonomy
| Bridge Table        | dimension_id, hierarchy_id  | Many-to-many hierarchies
| Explicit Levels     | l1_name, l2_name, l3_name   | Fixed-depth hierarchies

5.2 Parent-Child Implementation

```sql
CREATE TABLE dim_category_df (
    category_id       STRING      COMMENT 'Category ID',
    category_name     STRING      COMMENT 'Category Name',
    parent_id         STRING      COMMENT 'Parent Category ID',
    level_num         INT         COMMENT 'Hierarchy Level (1=root)',
    is_leaf           BOOLEAN     COMMENT 'Is Leaf Node',
    path_string       STRING      COMMENT 'Full path: L1>L2>L3',
    start_date        STRING      COMMENT 'SCD Start Date',
    end_date          STRING      COMMENT 'SCD End Date',
    is_current        BOOLEAN     COMMENT 'Is Current Version'
)
COMMENT 'Product Category Dimension with Hierarchy'
STORED AS PARQUET;

QUERY PATTERN FOR ROLLUP:
WITH RECURSIVE category_tree AS (
    SELECT category_id, parent_id, category_name, 0 AS depth
    FROM dim_category_df
    WHERE category_id = '${root_category}'
      AND is_current = TRUE
    UNION ALL
    SELECT c.category_id, c.parent_id, c.category_name, ct.depth + 1
    FROM dim_category_df c
    INNER JOIN category_tree ct ON c.parent_id = ct.category_id
    WHERE c.is_current = TRUE
)
SELECT * FROM category_tree;
```

5.3 Many-to-Many Hierarchies

Use bridge tables when an entity belongs to multiple hierarchies:
```sql
CREATE TABLE dim_product_category_bridge (
    product_id      STRING      COMMENT 'Product ID',
    category_id     STRING      COMMENT 'Category ID',
    is_primary      BOOLEAN     COMMENT 'Is Primary Category',
    sort_order      INT         COMMENT 'Display Order',
    effective_date  STRING      COMMENT 'Effective Start Date',
    expiry_date     STRING      COMMENT 'Effective End Date'
)
COMMENT 'Product-Category Many-to-Many Bridge';
```

6. ETL PATTERNS


6.1 Initial Load (Full)

PURPOSE: Populate dimension for the first time.

```sql
INSERT OVERWRITE TABLE dim_user_info_df PARTITION(dt='${biz_date}')
SELECT 
    user_id,
    user_name,
    city_code,
    '${biz_date}' AS start_date,
    '9999-12-31' AS end_date,
    TRUE AS is_current,
    1 AS version_id,
    CURRENT_TIMESTAMP() AS etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    '${source_system}' AS etl_source_system
FROM ods_pg_user_info_df
WHERE dt = '${biz_date}'
  AND user_id IS NOT NULL;
```

6.2 Daily Incremental (SCD Type 2 Merge)

PURPOSE: Handle inserts and updates with history tracking.

```sql
-- Step 1: Identify changes
WITH source_data AS (
    SELECT * FROM ods_pg_user_info_df WHERE dt = '${biz_date}'
),
current_dims AS (
    SELECT * FROM dim_user_info_df WHERE is_current = TRUE
),
changes AS (
    SELECT 
        s.user_id,
        s.user_name,
        s.city_code,
        c.city_code AS old_city_code
    FROM source_data s
    LEFT JOIN current_dims c ON s.user_id = c.user_id
    WHERE c.user_id IS NULL
       OR s.city_code != c.city_code
)

-- Step 2: Close old records
INSERT INTO dim_user_info_df
SELECT 
    c.user_id,
    c.user_name,
    c.city_code,
    c.start_date,
    DATE_SUB('${biz_date}', 1) AS end_date,
    FALSE AS is_current,
    c.version_id,
    c.etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    c.etl_batch_id,
    c.etl_source_system
FROM current_dims c
INNER JOIN changes ch ON c.user_id = ch.user_id;

-- Step 3: Insert new records
INSERT INTO dim_user_info_df
SELECT 
    user_id,
    user_name,
    city_code,
    '${biz_date}' AS start_date,
    '9999-12-31' AS end_date,
    TRUE AS is_current,
    COALESCE((SELECT MAX(version_id) + 1 FROM dim_user_info_df 
              WHERE user_id = ch.user_id), 1) AS version_id,
    CURRENT_TIMESTAMP() AS etl_create_time,
    CURRENT_TIMESTAMP() AS etl_update_time,
    '${batch_id}' AS etl_batch_id,
    '${source_system}' AS etl_source_system
FROM changes ch;
```

6.3 DDL Template (Databricks SQL)

```sql
CREATE TABLE IF NOT EXISTS {catalog}.dim_{domain}.dim_{entity}_scd2 (
    -- 1. Keys
    {entity}_sk       STRING          NOT NULL COMMENT 'Hash of ID + StartDate',
    {entity}_id       STRING          NOT NULL COMMENT 'Natural Business Key',
    
    -- 2. Descriptive Attributes (Denormalized Hierarchies)
    dim_level_l1      STRING          COMMENT 'Top Level (e.g. Category)',
    dim_level_l2      STRING          COMMENT 'Mid Level (e.g. Sub-Category)',
    dim_attr_name     STRING,
    
    -- 3. SCD2 Metadata
    start_date        DATE            NOT NULL,
    end_date          DATE            DEFAULT '9999-12-31',
    is_current        BOOLEAN         DEFAULT TRUE,
    row_hash          STRING          COMMENT 'SHA2 hash of attributes for change detection',
    
    -- 4. Audit & Lineage
    etl_inserted_at   TIMESTAMP       DEFAULT current_timestamp(),
    etl_batch_id      STRING,
    is_deleted_source BOOLEAN         DEFAULT FALSE COMMENT 'Flag if deleted in ODS'
)
USING DELTA
CLUSTER BY ({entity}_id, is_current) -- Liquid Clustering replaces PARTITION BY
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.targetFileSize' = '33554432' -- 32MB optimized for small dimensions
);
```
6.4 The "Hash-Based Merge"

To prevent "ghost updates" (where a timestamp changes but data doesn't), use a row_hash.

```sql
-- Step 1: Identify changes using hash comparison
-- Step 2: Expire old records (end_date = today, is_current = false)
-- Step 3: Insert new records (start_date = today, is_current = true)

-- For Modern Databricks: Use 'Delta Live Tables' or a 'Merge' with a subquery
MERGE INTO dim_user_scd2 AS target
USING (
    SELECT *, 
           sha2(concat_ws('||', user_name, city, level), 256) as current_hash
    FROM ods_user_info WHERE dt = '${biz_date}'
) AS source
ON target.user_id = source.user_id AND target.is_current = TRUE
WHEN MATCHED AND target.row_hash != source.current_hash THEN
  UPDATE SET target.end_date = current_date(), target.is_current = FALSE;

-- Followed by INSERT for source records where no active match exists.
```

7. DATA QUALITY RULES


7.1 Structural Checks

| Check                       | Rule                            | Threshold   | Action
| ----------------------------| --------------------------------| ------------| ------
| Surrogate Key Uniqueness    | COUNT(user_sk) = DISTINCT       | 100%        | Block
| Natural Key + Date Unique   | COUNT(*) = DISTINCT(key,date)   | 100%        | Block
| SCD Continuity              | No gaps in date ranges          | 100%        | Block
| Current Flag Consistency    | MAX 1 current per natural key   | 100%        | Block

7.2 Business Logic Checks

| Check                       | Rule                            | Threshold   | Action
| ----------------------------| --------------------------------| ------------| ------
| Hierarchy Integrity         | No cycles in parent-child       | 100%        | Block
| Leaf Node Validation        | is_leaf = TRUE has no children  | 100%        | Alert
| Code-Name Mapping           | One active name per code        | 100%        | Block
| Date Validity               | start_date <= end_date          | 100%        | Block

7.3 Completeness Checks

| Check                       | Rule                            | Threshold   | Action
| ----------------------------| --------------------------------| ------------| -----
| Mandatory Attributes        | No NULLs in required columns    | 100%        | Block
| Reference Integrity         | FK exist in parent dims         | >99.9%      | Alert
| Coverage vs. Source         | Count within 5% of source       | +/- 5%      | Alert


8. PERFORMANCE OPTIMIZATION


8.1 When to Denormalize Hierarchies

DENORMALIZE WHEN:
- Hierarchy depth is fixed and shallow (< 5 levels)
- Queries frequently need full path
- Dimension size is moderate (< 10M rows)

KEEP NORMALIZED WHEN:
- Hierarchy is deep or variable depth
- Frequent hierarchy changes
- Storage is constrained

DENORMALIZED STRUCTURE EXAMPLE:
```sql
CREATE TABLE dim_product_detail_df (
    product_id        STRING,
    product_name      STRING,
    category_l1_id    STRING,
    category_l1_name  STRING,
    category_l2_id    STRING,
    category_l2_name  STRING,
    category_l3_id    STRING,
    category_l3_name  STRING,
    start_date        STRING,
    end_date          STRING,
    is_current        BOOLEAN
);
```

8.2 Indexing Strategies

FOR SQL ENGINES SUPPORTING INDEXES:
-- Join key index
CREATE INDEX idx_dim_user_id ON dim_user_info_df(user_id) 
WHERE is_current = TRUE;

-- SCD query index
CREATE INDEX idx_dim_user_scd ON dim_user_info_df(user_id, start_date, end_date);

-- Hierarchy index
CREATE INDEX idx_dim_category_parent ON dim_category_df(parent_id) 
WHERE is_current = TRUE;

FOR COLUMNAR STORES (PARQUET/ORC):
- Sort by join key + is_current for efficient pruning
- Use Z-order clustering on frequently filtered columns

8.3 Broadcast Join Optimization

FOR SMALL DIMENSIONS (< 100MB):
SELECT /*+ BROADCAST(d) */
    f.order_id,
    d.user_name
FROM dwd_trade_order_fact f
JOIN dim_user_info_df d 
    ON f.user_id = d.user_id 
    AND d.is_current = TRUE;

CONFIGURATION:
spark.sql.autoBroadcastJoinThreshold = 104857600  -- 100MB

8.4 Partitioning Large Dimensions

FOR VERY LARGE DIMENSIONS (> 100M ROWS):
CREATE TABLE dim_user_info_df (
    ...
)
PARTITIONED BY (user_hash INT)
CLUSTERED BY (user_id) INTO 64 BUCKETS;

8.5 Hierarchy Denormalization

Standard: All hierarchies must be "Flattened" for ADS consumption.

- Rule: If a dimension has a Parent-Child relationship (Categories, Orgs), provide the full path as a string (e.g., Electronics > Audio > Headphones) and explicit columns for each level.

8.6 The "Current View" Pattern

For every SCD2 table, provide a view filtered on is_current = TRUE.

- Naming: v_dim_{entity}
- Benefit: BI tools like Power BI run faster when they don't have to filter every dimension by a WHERE clause.

8.7 Default "Unknown" Row

Every dimension must have a row with ID = -1 or ID = 'UNKNOWN'.

- Why: Ensures INNER JOIN in fact tables doesn't drop records when a dimension key is missing (Late-arriving data).

9. SECURITY & ACCESS


9.1 PII Handling

| Attribute       | Sensitivity     | Handling Strategy
| ----------------| ----------------| ----------------------------------------------
| user_name       | Medium          | Mask in non-production; encrypt at rest
| user_phone      | High            | Hash (SHA256) or tokenization
| user_email      | High            | Hash or partial mask (u***@domain.com)
| id_card         | Critical        | Encrypt with KMS; restrict access
| address         | Medium          | Generalize to city/region level

IMPLEMENTATION EXAMPLE:
```sql
SELECT 
    user_id,
    user_name,
    SHA2(phone, 256) AS phone_hash,
    CONCAT(SUBSTR(email, 1, 1), '***@', 
           SUBSTR(email, INSTR(email, '@') + 1)) AS email_masked
FROM ods_user_info;
```

9.2 Row-Level Security

ADD SECURITY MARKERS FOR MULTI-TENANT ACCESS:
```sql
CREATE TABLE dim_user_info_df (
    ...,
    dept_id STRING COMMENT 'Owning Department',
    access_level STRING COMMENT 'public|internal|confidential'
);
```

QUERY WITH SECURITY FILTER:
```sql
SELECT * FROM dim_user_info_df
WHERE is_current = TRUE
  AND (
    access_level = 'public'
    OR (access_level = 'internal' AND '${user_dept}' IS NOT NULL)
    OR (access_level = 'confidential' AND '${user_dept}' = dept_id)
  );
```

9.3 Column-Level Security

USE VIEWS TO RESTRICT SENSITIVE COLUMNS:
```sql
-- Public view (no PII)
CREATE VIEW v_dim_user_public AS
SELECT 
    user_id,
    user_name,
    city_code,
    user_level
FROM dim_user_info_df
WHERE is_current = TRUE;

-- Restricted view (with PII)
CREATE VIEW v_dim_user_restricted AS
SELECT * FROM dim_user_info_df WHERE is_current = TRUE;

-- Grant access
GRANT SELECT ON v_dim_user_public TO role_analyst;
GRANT SELECT ON v_dim_user_restricted TO role_data_steward;
```

10. COMMON DIMENSION PATTERNS


10.1 Date/Time Dimension

PRE-GENERATED, STATIC, TYPE 1.
```sql
CREATE TABLE dim_date_info_full (
    date_key          INT         COMMENT 'YYYYMMDD format',
    full_date         DATE        COMMENT 'Date object',
    day_of_week       INT         COMMENT '1=Sunday, 7=Saturday',
    day_name          STRING      COMMENT 'Monday, Tuesday, etc.',
    day_of_month      INT,
    day_of_year       INT,
    week_of_year      INT,
    month_name        STRING,
    month_of_year     INT,
    quarter           INT,
    year              INT,
    is_weekend        BOOLEAN,
    is_holiday        BOOLEAN,
    holiday_name      STRING
)
COMMENT 'Pre-generated calendar dimension'
STORED AS PARQUET;
```

10.2 User Dimension (SCD Type 2)

MOST COMMON PATTERN WITH HISTORY TRACKING.
```sql
CREATE TABLE dim_user_info_df (
    user_sk           BIGINT      COMMENT 'Surrogate Key',
    user_id           STRING      COMMENT 'Natural Key',
    user_name         STRING,
    gender            STRING,
    age_bucket        STRING,
    city_code         STRING,
    user_level        STRING,
    register_date     STRING,
    start_date        STRING,
    end_date          STRING,
    is_current        BOOLEAN,
    version_id        BIGINT,
    etl_create_time   TIMESTAMP,
    etl_update_time   TIMESTAMP
)
COMMENT 'User Dimension with SCD Type 2 History'
PARTITIONED BY (dt STRING)
STORED AS PARQUET;
```

10.3 Product Dimension (Hierarchical)

WITH DENORMALIZED CATEGORY PATH FOR PERFORMANCE.
```sql
CREATE TABLE dim_product_detail_df (
    product_sk        BIGINT,
    product_id        STRING,
    product_name      STRING,
    brand_name        STRING,
    category_l1_id    STRING,
    category_l1_name  STRING,
    category_l2_id    STRING,
    category_l2_name  STRING,
    category_l3_id    STRING,
    category_l3_name  STRING,
    category_path     STRING COMMENT 'L1>L2>L3',
    price             DECIMAL(18,2),
    weight_kg         DECIMAL(10,2),
    is_active         BOOLEAN,
    start_date        STRING,
    end_date          STRING,
    is_current        BOOLEAN
)
COMMENT 'Product Dimension with Denormalized Hierarchy'
PARTITIONED BY (dt STRING)
STORED AS PARQUET;
```

10.4 Geography Dimension (Multiple Hierarchies)

SUPPORTS BOTH ADMINISTRATIVE AND SALES HIERARCHIES.

```sql
CREATE TABLE dim_geo_region_df (
    region_sk         BIGINT,
    region_id         STRING,
    region_name       STRING,
    region_type       STRING COMMENT 'country|province|city|district',
    admin_parent_id   STRING,
    admin_level       INT,
    sales_region_id   STRING,
    sales_zone        STRING,
    latitude          DECIMAL(10,6),
    longitude         DECIMAL(10,6),
    start_date        STRING,
    end_date          STRING,
    is_current        BOOLEAN
)
COMMENT 'Geography Dimension with Dual Hierarchies'
PARTITIONED BY (dt STRING)
STORED AS PARQUET;
```

10.5 Junk Dimension (Flags and Statuses)

COMBINE LOW-CARDINALITY ATTRIBUTES INTO ONE DIMENSION.

```sql
CREATE TABLE dim_order_flags_df (
    flag_sk           BIGINT,
    is_gift           BOOLEAN,
    is_express        BOOLEAN,
    is_cod            BOOLEAN COMMENT 'Cash on Delivery',
    payment_channel   STRING COMMENT 'online|offline|mixed',
    order_source      STRING COMMENT 'app|web|third_party',
    is_current        BOOLEAN
)
COMMENT 'Junk Dimension for Order Flags'
STORED AS PARQUET;
```

USAGE IN FACT TABLE:
SELECT f.*, j.is_gift, j.is_express
FROM dwd_order_fact f
JOIN dim_order_flags_df j 
    ON f.is_gift = j.is_gift 
    AND f.is_express = j.is_express;


11. RETENTION POLICY


| Dimension Type          | Retention Period        | Archival Strategy
| ------------------------| ------------------------| ------------------------------
| Transactional (SCD 2)   | Keep all history        | Move versions > 3 years to cold storage
| Reference (static)      | Indefinite              | No archival; small size
| Junk Dimensions         | Indefinite              | No archival; small size
| Date Dimension          | Indefinite              | Pre-generated; no changes


12. MONITORING & ALERTING


12.1 Metrics to Track

- Dimension record count by type (new/updated/unchanged)
- SCD change rate (percentage of records with changes)
- Orphan fact rate (facts referencing non-existent dimensions)
- Join performance (avg time for dimension lookups)
- PII access audit logs

12.2 Alert Thresholds

| Condition                           | Severity        | Notification
| ------------------------------------| ----------------| --------------------------
| SCD merge failure                   | Critical        | Page on-call
| Orphan rate > 1%                    | High            | Slack + Email
| Dimension growth > 50% day-over-day | Medium          | Email
| PII access from unauthorized role   | Critical        | Page security team


13. BEST PRACTICES


DO:
- Use SCD Type 2 for analytical attributes
- Maintain is_current flag for efficient querying
- Document hierarchy relationships clearly
- Pre-generate static dimensions (date, time)
- Hash or mask PII during ETL, not in queries
- Test SCD logic with historical change scenarios
- Version dimension ETL jobs for reproducibility

DON'T:
- Overuse SCD Type 2 for non-analytical attributes
- Leave NULL natural keys unhandled
- Create duplicate conformed dimensions
- Skip validation of hierarchy integrity
- Store raw PII in dimensions accessible to all users
- Assume dimension keys are stable; always validate


14. COMMON PITFALLS


PITFALL: SCD Explosion  
SOLUTION: Monitor dimension growth; archive old versions; consider Type 1 for low-value attributes  

PITFALL: Hierarchy Cycles  
SOLUTION: Validate parent-child relationships during ETL; use graph algorithms to detect cycles  

PITFALL: Late-Arriving Dimensions Breaking Facts  
SOLUTION: Implement placeholder strategy; design fact ETL to handle missing dimensions gracefully  

PITFALL: Inconsistent Conformed Dimensions  
SOLUTION: Centralize dimension ownership; require architecture review for new dimensions  

PITFALL: Performance Degradation on Large Dimensions  
SOLUTION: Implement broadcast hints; consider mini-dimensions; optimize partitioning  


15. RELATED DOCUMENTS


- references/ODS_DESIGN.md - Upstream source specifications
- references/DWD_DESIGN.md - Fact table join patterns
- references/DWS_DESIGN.md - Aggregation using dimensions
- references/ADS_DESIGN.md - Downstream layer specifications
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards
