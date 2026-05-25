STAR SCHEMA DESIGN


Document ID: STAR-SCHEMA-DESIGN 
Last Updated: 2026-05-25   
Author: Jing Ge https://github.com/JingGe  

1. OVERVIEW

1.1 Purpose
This document defines the logical modeling standards for designing star schema structures within the data warehouse. It provides rules for fact tables, dimension tables, and relationships to ensure:
- Consistent analytical semantics across all layers
- Correct aggregation behavior for metrics
- Query performance through proper schema design
- Maintainability and extensibility of data models

1.2 Scope
This standard applies to:
- All fact tables in DWD, DWM, DWS, and ADS layers
- All dimension tables in DIM layer
- Any denormalized structures in ADS that follow dimensional patterns

1.3 Core Principles
1. Grain First: Always define the grain before designing any table
2. Conformed Dimensions: Reuse dimensions across fact tables
3. Additive Measures: Design facts to support additive aggregation where possible
4. Denormalize for Performance: Embed dimension attributes in facts when beneficial
5. Document Everything: Every grain, key, and measure must be documented


2. CORE PRINCIPLES

2.1 Grain First
Rule: Define grain before any table design.
One row per [business event/entity] at [lowest level of detail].

Validation:
- Can two rows have the same foreign key combination? If yes, grain is too coarse.
- Can one business event produce multiple rows? If yes, grain is too fine.

1.2 Conformed Dimensions
Rule: Dimensions used by multiple facts must be identical (same keys, attributes, SCD strategy).

Register conformed dimensions in: references/DIM_DESIGN.md

1.3 Measure Classification
Rule: Every measure must be classified before aggregation logic is defined.

| Type          | Aggregation Rule             | Example                     |
|---------------|------------------------------|-----------------------------|
| Additive      | SUM() across all dimensions  | order_amount, quantity      |
| Semi-Additive | SUM() across some dims only  | inventory_balance           |
| Non-Additive  | AVG()/MIN()/MAX()/ratio only | unit_price, conversion_rate |


2. FACT TABLE DESIGN RULES

Rule: Every fact table must have a clearly documented grain statement.

Grain Statement Format:
One row per [business event/entity] at [lowest level of detail] for [time scope].

Examples:
| Table                  | Grain Statement                                              |
|------------------------|--------------------------------------------------------------|
| dwd_trade_order_di     | One row per order line item at the time of order creation    |
| dwd_user_login_di      | One row per user login session                               |
| dws_user_action_1d_di  | One row per user per calendar day                            |
| dws_user_action_7d_nd  | One row per user for the rolling 7-day window ending on dt   |

Validation:
- Can two rows have the same foreign key combination? If yes, grain is too coarse.
- Can one business event produce multiple rows? If yes, grain is too fine.
- Is the grain stable over time (not dependent on future business changes)?


2.1 Fact Types

| Type                  | Grain                         | Use When                        |
|-----------------------|-------------------------------|---------------------------------|
| Transaction           | One row per event             | Recording business transactions |
| Periodic Snapshot     | One row per entity per period | Capturing state at intervals    |
| Accumulating Snapshot | One row per process instance  | Tracking lifecycle progress     |

Implementation: See references/DWD_DESIGN.md for DWD, references/DWS_DESIGN.md for DWS

2.2 Foreign Keys
- Use surrogate keys (sk) for joins
- Include natural keys as degenerate dimensions
- Allow NULL for optional dimensions
- Never join fact-to-fact directly

2.3 Foreign Key Rules

Rule: All foreign keys in fact tables must reference dimension primary keys.

Requirements:

```sql
-- Fact table foreign keys
CREATE TABLE dwd_trade_order_di (
    -- Foreign keys (must match dimension PKs)
    user_sk           BIGINT NOT NULL,  -- References dim_user_info.user_sk
    product_sk        BIGINT NOT NULL,  -- References dim_product_detail.product_sk
    date_sk           BIGINT NOT NULL,  -- References dim_date_info.date_sk
    
    -- ... measures ...
);
```

Best Practices:

- Use surrogate keys (sk) for joins, not natural keys
- Include natural keys as degenerate dimensions for debugging
- Always allow NULL for optional dimensions (e.g., promo_sk)
- Document the dimension relationship in column comments

3. DIMENSION TABLE DESIGN RULES

3.1 Conformed Dimensions
Rule: Dimensions used by multiple fact tables must be conformed (identical structure and values).
Conformance Checklist:

- Same surrogate key generation logic
- Same attribute names and data types
- Same SCD strategy for each attribute
- Same hierarchy definitions
- Same code mappings and enumerations

3.2 When to Degenerate
Rule: Embed dimension attributes in fact tables when they are frequently queried and rarely change.

When to Degenarate:

- Attribute is used in > 80% of queries against the fact
- Dimension table is small (< 1M rows) or attribute is SCD Type 1
- Join performance is critical and attribute is low-cardinality
- Attribute is transactional (e.g., order_number, invoice_id)

When NOT to Degenarate:

- Attribute changes frequently (SCD Type 2 needed)
- Dimension is large and shared across many facts
- Attribute is rarely used in queries
- Storage cost is a concern

3.3 Junk Dimensions
Rule: Combine multiple low-cardinality flags and statuses into a single junk dimension.

When to Use:

- Multiple boolean or low-cardinality attributes (2-10 distinct values each)
- Attributes are independent (no hierarchical relationship)
- Attributes are used together in filtering or grouping

Example: is_gift, is_express, payment_channel, order_source → single junk dimension

3.4 SCD Strategy Quick Reference


| Impact                        | SCD Type              | Examples                        |
|-------------------------------|-----------------------|---------------------------------|
| No analytical impact          | Type 1 (Overwrite)    | name, phone, email              |
| Affects historical analysis   | Type 2 (Add Row)      | city, segment, category         |


3.5 Role-Playing Dimensions

Rule: Use the same dimension table multiple times with different aliases for different roles.
Example: Date Dimension in Order Fact

```sql
-- Fact table has multiple date foreign keys
CREATE TABLE dwd_trade_order_di (
    -- ... other keys ...
    order_date_sk     BIGINT COMMENT 'When order was placed',
    payment_date_sk   BIGINT COMMENT 'When payment was received',
    ship_date_sk      BIGINT COMMENT 'When order was shipped',
    deliver_date_sk   BIGINT COMMENT 'When order was delivered'
);


-- Query: analyze order-to-delivery cycle
SELECT 
    d_order.year AS order_year,
    d_deliver.year AS deliver_year,
    AVG(DATEDIFF(f.deliver_date_sk, f.order_date_sk)) AS avg_delivery_days
FROM dwd_trade_order_di f
JOIN dim_date_info_full d_order ON f.order_date_sk = d_order.date_sk
JOIN dim_date_info_full d_deliver ON f.deliver_date_sk = d_deliver.date_sk
GROUP BY d_order.year, d_deliver.year;
```

Best Practice: Document each role in column comments and use consistent alias naming (d_order, d_payment, etc.).

4. FORBIDDEN ANTI-PATTERNS

4.1 Snowflaking
Forbidden: Normalizing dimension attributes into multiple tables.
Required: Denormalize hierarchies into single dimension table.
Exception: Requires architecture approval if dimension >10M rows and static.

4.2 Many-to-Many Facts
Forbidden: Multiple foreign keys to same dimension in one fact row.
Required: One row per atomic grain. Use bridge table for true M:M relationships.

4.3 Mixed Grains
Forbidden: Combining header and line-level data in one fact table.
Required: Separate tables for each grain level.

4.4 Wide Flat Tables
Forbidden: >200 columns without justification.
Required: Split into core fact + satellite tables for rarely-used attributes.

4.5 Wrong Measure Aggregation
Forbidden: Summing non-additive measures or averaging averages.
Required: Use weighted calculations for rates and ratios.

5. DESIGN CHECKLIST

5.1 Fact Table Design Checklist

Before finalizing a fact table design, verify:
Grain and Keys:

- Grain statement is documented and unambiguous
- All foreign keys reference dimension surrogate keys
- Natural keys are included as degenerate dimensions for debugging
- Surrogate keys are used for joins (not natural keys)

Measures:

- Every measure is classified as additive, semi-additive, or non-additive
- Aggregation rules are documented for each measure
- Non-additive measures are not summed in example queries
- Derived measures use correct weighted calculations

Structure:

- Table follows star schema (facts reference dimensions, not other facts)
- Degenerate dimensions are used appropriately
- Junk dimension is considered for low-cardinality flags
- No snowflaking without explicit approval

Performance:

- Partitioning strategy aligns with query patterns
- Clustering/Z-Order keys are defined for high-cardinality filters
- Expected data volume is documented for capacity planning

5.2 Dimension Table Design Checklist

Before finalizing a dimension table design, verify:
Conformance:

- Dimension is registered in the conformed dimension catalog
- Attribute names and types match other uses of this dimension
- SCD strategy is consistent with other fact tables using this dimension

SCD Strategy:

- Each attribute has an explicit SCD type assignment
- Type 2 attributes include start_date, end_date, is_current columns
- Type 1 attributes are documented as overwrite-safe
- Hash columns are used for efficient change detection (Type 2)

Hierarchy:

- Hierarchical attributes are denormalized (not snowflaked)
- Path or level columns are included for rollup queries
- Parent-child relationships are documented if used

Usability:

- Human-readable names are included (not just codes)
- Common filters have appropriate data types
- Null handling is documented for optional attributes

5.3 Anti-Pattern Review Checklist

Before approving a design, confirm none of these anti-patterns are present:

- No snowflaking without architecture approval
- No many-to-many facts without bridge table
- No wide flat tables (> 200 columns) without justification
- No mixing of grains in a single fact table
- No summing of non-additive measures in documentation or examples
- No direct joins between fact tables (always join via dimensions)

6. RELATED DOCUMENTS

- references/ODS_DESIGN.md - ODS layer specifications
- references/DWD_DESIGN.md - DWD layer specifications
- references/DWM_DESIGN.md - DWM layer specifications
- references/DIM_DESIGN.md - DIM layer specifications
- references/DWS_DESIGN.md - DWS layer specifications
- references/ADS_DESIGN.md - ADS layer specifications
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards