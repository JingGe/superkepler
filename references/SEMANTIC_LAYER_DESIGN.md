# SEMANTIC LAYER DESIGN DOCUMENT

Document ID: SEMANTIC-LAYER-DESIGN  
Last Updated: 2026-08-31  
Author: Jing Ge https://github.com/JingGe


1. PURPOSE


The semantic layer sits on top of the data model as a business abstraction. It maps pre-aggregated DWS facts to human-readable metrics, handles runtime mathematics that cannot be pre-computed, and enforces authorization rules — all without duplicating data modeling logic.

The canonical data flow is:

  Source Systems -> ODS -> DWD -> DWM -> DWS -> Semantic Layer -> BI / API / ML

Building a semantic layer without a properly designed data model underneath is like building a roof directly on the ground. The semantic layer can only be as correct and performant as the DWS tables it sits on.

1.1 Single Source of Truth: DWS + Semantic Layer Together

DWS and the semantic layer together form the single source of truth. Neither is sufficient alone:

- DWS is the authoritative source for additive facts: pay_amt, order_cnt, gmv. If DWS
  defines pay_amt inconsistently, every downstream ratio built on it is wrong regardless
  of how correct the semantic layer formula is.

- The semantic layer is the authoritative source for derived business metrics: conversion_rate,
  AOV, MTD revenue. It solves the fragmentation problem — the same metric calculated
  differently across dozens of reports and teams.

The division of responsibility is precise:

  DWS owns:            additive facts (SUM/COUNT with no division, fixed windows)
  Semantic layer owns: non-additive ratios, runtime time windows, cross-metric KPIs,
                       business naming, and authorization

The invariant: if you can write it as SUM(column) or COUNT(column) with no division
and no runtime-chosen time window, it belongs in DWS. Everything else belongs in
the semantic layer.


2. THE BOUNDARY: DWS VS SEMANTIC LAYER


The key architectural decision is what belongs in DWS (pre-computed, materialized) versus what belongs in the semantic layer (runtime, calculated on query).

Use the following two questions as the decision framework:

  Q1: Is this metric additive across its natural grain?
  Q2: Is the time window fixed or analyst-chosen at runtime?

┌──────────────────────────────────────┬─────────────┬────────────────────────────────────────────┐
│                Answer                │  Put it in  │                   Reason                   │
├──────────────────────────────────────┼─────────────┼────────────────────────────────────────────┤
│ Additive + fixed window              │ DWS         │ Pre-aggregate once, SUM cheaply downstream │
├──────────────────────────────────────┼─────────────┼────────────────────────────────────────────┤
│ Non-additive (ratio, distinct count) │ Metric View │ Cannot safely pre-aggregate                │
├──────────────────────────────────────┼─────────────┼────────────────────────────────────────────┤
│ Additive + runtime window            │ Metric View │ Hardcoding creates column explosion        │
├──────────────────────────────────────┼─────────────┼────────────────────────────────────────────┤
│ Fixed window but expensive join      │ DWS         │ Materialise once, avoid repeated cost      │
└──────────────────────────────────────┴─────────────┴────────────────────────────────────────────┘

See section 1.1 for the invariant.


3. WHAT BELONGS IN DWS (PRE-AGGREGATED)


Pre-aggregate in DWS when the metric is additive at its natural grain and the time window is fixed.
These metrics can be SUM-ed safely at any higher grain.

| Category              | Examples
| ----------------------| ----------------------------------------------------
| Additive counts       | login_cnt, order_cnt, pv_cnt, pay_cnt, refund_cnt
| Additive amounts      | order_amt, pay_amt, refund_amt, gmv
| Fixed retention       | 7-day retention count, 30-day retention count
| Additive time markers | last_login_time, first_order_time (MAX/MIN)

Note: fixed retention windows (7/30/60 days) make sense to pre-compute in DWS because they
are always queried at the same grain and window. They are the exception, not the rule.


4. WHAT BELONGS IN THE SEMANTIC LAYER (RUNTIME)


Keep in the metric view when the metric is non-additive or uses an analyst-chosen time window.

4.1 Non-Additive Ratios (Dynamic Run-Time Mathematics)

Ratios and rates cannot be pre-aggregated because percentages cannot be added together.
Pre-computing "Conversion Rate" in DWS for user A and user B gives the wrong result when
summing to get the overall rate.

| Metric                  | Formula                                  | Why not DWS
| ------------------------| -----------------------------------------| ---------------------------
| Conversion Rate         | SUM(pay_cnt) / COUNT(order_cnt)          | Ratio — not additive
| Average Order Value     | SUM(pay_amt) / SUM(pay_cnt)              | Ratio — not additive
| Engagement Rate         | SUM(is_engaged) / COUNT(*)               | Ratio — not additive
| Click-Through Rate      | SUM(clicks) / SUM(impressions)           | Ratio — not additive
| Avg Conversation Depth  | SUM(turns) / COUNT(conversations)        | Ratio — not additive
| HVA Rate                | SUM(is_hva) / COUNT(*)                   | Ratio — not additive

4.2 Runtime Time Intelligence (Dynamic Slicing Windows)

When the time window is analyst-chosen at query time, hardcoding it in DWS creates
a column explosion (MTD_revenue, YTD_revenue, WTD_revenue, ...).

| Pattern                 | Examples
| ------------------------| ----------------------------------------------------
| Period-to-date          | Month-to-date revenue, Year-to-date GMV
| Week-over-week          | Revenue WoW change, orders WoW growth rate
| Rolling analyst window  | Rolling 14-day (not pre-built as a DWS table)
| Cohort day-N retention  | Day-1, Day-7, Day-N retention by cohort

Exception: common fixed windows (7d, 30d, 60d retention) may be pre-built in DWS
if they are always queried at the same grain. See DWS_DESIGN.md section 6.5.

4.3 Cross-Metric Derived KPIs

When a KPI depends on two or more independently defined metrics, keep the derivation
in the semantic layer. This ensures that if the underlying metric definition changes,
all dependent KPIs update automatically.

| KPI                     | Depends On
| ------------------------| ----------------------------------------------------
| Profit Margin           | Revenue metric + Cost metric
| GMV per HVA User        | GMV metric + HVA user count metric
| Cost per Conversion     | Marketing cost metric + conversion count metric
| Net Revenue             | Gross revenue metric + Refund amount metric


5. SEMANTIC LAYER JOINS: DWS TO DWS ONLY


The semantic layer must only join DWS tables to DWS tables.

NEVER join DWD or DWM tables in a metric view. DWD tables are inputs to the ETL
pipeline — querying them in the semantic layer bypasses the presentation layer and
creates performance and maintainability problems.

If a join requires a DWD table, that DWD table must first be promoted to a DWS table.

  Allowed:   Metric View -> dws_trade_order_1d_di JOIN dws_user_action_1d_di
  Forbidden: Metric View -> dwd_trade_order_di  (bypasses DWS)
  Forbidden: Metric View -> dwm_trade_order_merge_di  (bypasses DWS)


6. METRIC VIEW DESIGN PRINCIPLES


6.1 One metric, one definition

Each business metric must have exactly one canonical definition in the semantic layer.
Duplicate definitions across different metric views will diverge over time.

6.2 Compose from atomic DWS columns

Metric views reference raw additive columns from DWS (pay_amt, pay_cnt, order_cnt),
not pre-computed derived columns (avg_order_value, conversion_rate). The semantic
layer owns the ratio logic.

6.3 Name metrics in business language

DWS columns use technical names (pay_amt, pay_cnt). The semantic layer maps these
to business names (Revenue, Order Count) with clear descriptions.

6.4 Document the formula

Every metric definition must document its formula, the DWS columns it references,
and any filter conditions applied (e.g., "exclude refunded orders").


7. EXAMPLE: DWS COLUMNS VS METRIC VIEW DEFINITIONS


DWS table supplies additive raw columns (correct):

```sql
-- dws_trade_order_1d_di: additive columns only
order_cnt    BIGINT   COMMENT 'Number of orders placed',
pay_cnt      BIGINT   COMMENT 'Number of paid orders',
pay_amt      DECIMAL  COMMENT 'Total payment amount',
refund_cnt   BIGINT   COMMENT 'Number of refunded orders',
refund_amt   DECIMAL  COMMENT 'Total refund amount'
-- NO avg_order_value, NO conversion_rate — these belong in the semantic layer
```

Metric view defines non-additive metrics at runtime (correct):

```sql
-- Databricks Metric View (semantic layer)
CREATE METRIC VIEW trade_metrics AS
SELECT
    dt,
    user_id,
    -- Additive metrics passed through directly
    pay_amt       AS revenue,
    pay_cnt       AS paid_order_count,
    order_cnt     AS order_count,
    -- Non-additive ratios defined here, not in DWS
    MEASURE pay_amt / NULLIF(pay_cnt, 0)     AS avg_order_value,
    MEASURE pay_cnt / NULLIF(order_cnt, 0)   AS conversion_rate,
    MEASURE (pay_amt - refund_amt) / NULLIF(pay_amt, 0) AS net_revenue_rate
FROM catalog.schema.dws_trade_order_1d_di;
```


8. COMMON MISTAKES


Mistake: Pre-computing conversion_rate in DWS
Problem: SUM(conversion_rate) across users gives a wrong result — you cannot add rates.
Fix: Keep pay_cnt and order_cnt as additive columns in DWS; compute the ratio in the metric view.

Mistake: Joining DWD tables in a metric view for "freshness"
Problem: Bypasses the DWS presentation layer, causes performance problems and tight coupling.
Fix: Promote the required DWD columns to a DWS table first.

Mistake: Hardcoding MTD / YTD columns in DWS
Problem: Creates column explosion; every new time window requires a schema change.
Fix: Keep a 1d DWS table with daily additive metrics; let the semantic layer compute period-to-date at runtime.

Mistake: Different teams defining "Revenue" differently in their own metric views
Problem: Fragmentation — the same metric means different things across reports.
Fix: Define Revenue once in a shared base metric view; other views reference it.


9. RELATED DOCUMENTS


- references/DWS_DESIGN.md - DWS layer — the direct upstream of the semantic layer
- references/ADS_DESIGN.md - ADS layer — application-specific products, alternative to semantic layer for fixed reports
- references/NAMING_CONVENTION.md - Naming standards
- references/SQL_STANDARDS.md - SQL coding standards
