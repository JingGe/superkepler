NAMING CONVENTION STANDARD


Document ID: NAMING-CONVENTION  
Version: 1.0.0  
Last Updated: 2026-03-22  
Author: Jing Ge https://github.com/JingGe  


1. OVERVIEW


This document defines the comprehensive naming convention for all tables, columns, and objects in the data warehouse. Consistent naming ensures:

- Discoverability: Easy to find tables by name
- Maintainability: Clear purpose from table name
- Automation: Scripts can parse and process tables programmatically
- Governance: Enforce standards across teams

2. GENERAL NAMING RULES


2.1 Character Rules

| Rule                | Description             | Example
| --------------------| ------------------------| ------------------
| Lowercase Only      | All names lowercase     | dwd_trade_order (Valid)
| Underscore Sep      | Use _ between words     | user_info (Valid)
| No Special Chars    | No -, @, #, spaces      | user-info (Invalid)
| No Reserved Words   | Avoid SQL keywords      | select, order (Invalid)
| Max Length          | Keep under 64 chars     | Hive/MySQL compatibility

2.2 Language Rules

| Component           | Language                | Example
| --------------------| ------------------------| ------------------
| Layer Prefix        | English (abbreviated)   | ods, dwd, dws
| Domain              | English (lowercase)     | trade, user, log
| Entity              | English (lowercase)     | order, info, action
| Comments            | English                 | English

3. TABLE NAMING CONVENTION


3.1 Syntax Structure

{layer}_{domain}_{entity}_{granularity}_{suffix}

| Component       | Required      | Description             | Examples
| ----------------| --------------| ------------------------| --------
| layer           | Yes           | Data warehouse layer    | ods, dim, dwd, dws, ads
| domain          | Yes           | Business domain         | trade, user, log, finance
| entity          | Yes           | Core business object    | order, payment, info
| granularity     | No            | Time/aggregation level  | 1d, 7d, 30d, hour
| suffix          | Yes           | Loading strategy        | di, df, hi, nd, rt, full

3.2 Layer-Specific Patterns

ODS Layer:
Pattern: ods_{source_system}_{table_name}_{suffix}
Examples:
- ods_mysql_trade_orders_di
- ods_mysql_user_info_df
- ods_traffic_app_clicks_hi

DIM Layer:
Pattern: dim_{domain}_{entity}_{suffix}
Examples:
- dim_user_info_df
- dim_product_detail_df
- dim_shop_info_df

DWD Layer:
Pattern: dwd_{domain}_{entity}_{suffix}
Examples:
- dwd_trade_order_di
- dwd_trade_order_detail_di
- dwd_user_login_di

DWM Layer:
Pattern: dwm_{domain}_{entity}_{processing}_{suffix}
Examples:
- dwm_trade_order_merge_di
- dwm_user_behavior_calc_di
- dwm_finance_payment_enrich_df

DWS Layer:
Pattern: dws_{domain}_{entity}_{granularity}_{suffix}
Examples:
- dws_user_action_1d_di
- dws_user_action_7d_nd
- dws_user_action_30d_nd

ADS Layer:
Pattern: ads_{app_name}_{metric}_{suffix}
Examples:
- ads_exec_kpi_daily_df
- ads_mkt_campaign_result_di
- ads_crm_user_label_df

4. LOADING STRATEGY SUFFIXES


| Suffix      | Full Name               | Frequency       | Use Case
| ------------| ------------------------| ----------------| ----------
| di          | Daily Incremental       | Once per day    | Transactional facts
| df          | Daily Full Snapshot     | Once per day    | State tables, dimensions
| hi          | Hourly Incremental      | Every hour      | High-frequency logs
| hf          | Hourly Full Snapshot    | Every hour      | Real-time state
| nd          | N-Day Rolling           | Daily           | DWS cumulative windows
| rt          | Real-Time               | Streaming       | Low-latency serving
| full        | Static Full Load        | One-time        | Reference tables
| inc         | Generic Incremental     | Variable        | Custom incremental

Suffix Selection Guide:

Is the data transactional (new records daily)?
- YES -> Use di (Daily Incremental)
- NO -> Is it a state snapshot?
    - YES -> Use df (Daily Full Snapshot)
    - NO -> Is it hourly?
        - YES -> Use hi or hf
        - NO -> Is it a rolling window (DWS)?
            - YES -> Use nd
            - NO -> Use full (static)

5. COLUMN NAMING CONVENTION


5.1 Syntax Structure

{attribute}_{unit_or_type}

5.2 Common Attribute Prefixes

| Prefix          | Description             | Examples
| ----------------| ------------------------| ----------------------
| user_           | User-related            | user_id, user_name, user_level
| order_          | Order-related           | order_id, order_time, order_status
| product_        | Product-related         | product_id, product_name, product_price
| pay_            | Payment-related         | pay_id, pay_time, pay_amount
| login_          | Login-related           | login_time, login_ip, login_device
| shop_           | Shop-related            | shop_id, shop_name, shop_type
| mkt_            | Marketing-related       | mkt_id, mkt_channel, mkt_campaign

5.3 Common Suffixes

| Suffix          | Type                    | Examples
| ----------------| ------------------------| ----------------------
| _id             | Identifier              | user_id, order_id, product_id
| _name           | Name/Label              | user_name, product_name, city_name
| _code           | Code/Enum               | country_code, currency_code, status_code
| _time           | Timestamp               | create_time, update_time, login_time
| _date           | Date only               | birth_date, register_date, order_date
| _cnt            | Count                   | login_cnt, order_cnt, pv_cnt
| _amt            | Amount (money)          | order_amt, pay_amt, refund_amt
| _rate           | Rate/Ratio              | conversion_rate, growth_rate, retention_rate
| _flag           | Boolean flag            | is_active, is_vip, is_deleted
| _type           | Type/Category           | device_type, order_type, user_type
| _level          | Level/Grade             | user_level, vip_level, risk_level
| _avg            | Average                 | avg_order_value, avg_duration
| _max            | Maximum                 | max_order_amount, max_login_cnt
| _min            | Minimum                 | min_order_amount, min_login_cnt

5.4 Column Naming Examples

| Good                | Bad                 | Reason
| --------------------| --------------------| ----------------------
| user_id             | uid, UserId         | Consistent prefix, lowercase
| order_amount        | amt, orderAmt       | Clear, snake_case
| login_count         | cnt, loginCnt       | Full word or standard abbreviation
| is_active           | active, active_flag | Boolean prefix is_
| create_time         | ctime, created_at   | Consistent with team standard

6. PARTITION COLUMN NAMING


| Partition Type    | Column Name    | Format          | Example
| ------------------| ---------------| ----------------| -------------
| Daily             | dt             | yyyy-MM-dd      | dt='2023-10-27'
| Hourly            | dt, hh         | yyyy-MM-dd, HH  | dt='2023-10-27', hh='12'
| Monthly           | month          | yyyy-MM         | month='2023-10'
| Regional          | region         | String code     | region='cn-east'

Rule: Always use dt for daily partitions (never date, partition_date, biz_date in DDL).

7. TEMPORARY & INTERMEDIATE TABLES


7.1 Temporary Tables (Session)

Pattern: tmp_{purpose}_{timestamp}

Examples:
- tmp_order_clean_20231027
- tmp_user_merge_20231027

Lifecycle: Auto-delete after 7 days

7.2 Intermediate Tables (ETL Staging)

Pattern: int_{layer}_{purpose}_{suffix}

Examples:
- int_dwd_order_staging_di
- int_dws_user_calc_nd

Lifecycle: Can be kept for debugging, document retention

8. VIEW NAMING CONVENTION
-------------------------

Pattern: {type}_{layer}_{purpose}

| Type                | Prefix      | Description
| --------------------| ------------| ------------------------------
| Standard View       | v_          | Regular view
| Materialized View   | mv_         | Pre-computed view
| Security View       | sv_         | Row-level security

Examples:
- v_dwd_order_summary
- mv_ads_kpi_daily
- sv_user_dept_filtered

9. NAMING VALIDATION CHECKLIST
------------------------------

Before creating any table, verify:

- [ ] Table name is all lowercase
- [ ] Words separated by underscores (no camelCase)
- [ ] Layer prefix is correct (ods, dim, dwd, dwm, dws, ads)
- [ ] Loading strategy suffix is included (di, df, nd, etc.)
- [ ] No SQL reserved words used
- [ ] Name is under 64 characters
- [ ] Column names follow attribute_suffix pattern
- [ ] Partition column is named dt (for daily)
- [ ] All columns have comments
- [ ] Table has a comment

10. COMMON NAMING MISTAKES


| Mistake                  | Wrong Example         | Correct Example
| -------------------------| ----------------------| ---------------
| Missing layer prefix     | user_order_daily      | dws_user_order_1d_di
| Missing suffix           | dwd_trade_order       | dwd_trade_order_di
| CamelCase                | dwdTradeOrderDi       | dwd_trade_order_di
| Inconsistent granularity | dws_user_daily        | dws_user_action_1d_di
| Abbreviation overload    | dws_usr_ord_1d        | dws_user_order_1d_di
| Wrong suffix             | dws_user_7d_di        | dws_user_7d_nd
| Special characters       | dwd-order_info        | dwd_order_info_di

11. NAMING DECISION TREE


Start: What layer is this table?
|
|-- ODS -> ods_{source}_{table}_{suffix}
|   |-- Incremental? -> di or hi
|   |-- Snapshot? -> df or hf
|
|-- DIM -> dim_{domain}_{entity}_{suffix}
|   |-- Daily snapshot? -> df
|   |-- Static? -> full
|
|-- DWD -> dwd_{domain}_{entity}_{suffix}
|   |-- Transactional? -> di
|   |-- State? -> df
|   |-- Hourly? -> hi
|
|-- DWM -> dwm_{domain}_{entity}_{processing}_{suffix}
|   |-- Merge? -> merge_di
|   |-- Calculate? -> calc_di
|   |-- Enrich? -> enrich_df
|
|-- DWS -> dws_{domain}_{entity}_{granularity}_{suffix}
|   |-- 1-day aggregate? -> 1d_di
|   |-- Rolling window? -> 7d_nd, 30d_nd
|
|-- ADS -> ads_{app}_{metric}_{suffix}
    |-- Dashboard? -> df
    |-- Incremental report? -> di
    |-- Real-time? -> rt

12. AUTOMATION & ENFORCEMENT


12.1 Regex Patterns for Validation

# ODS Layer
^ods_[a-z]+_[a-z]+_(di|df|hi|hf|inc)$

# DIM Layer
^dim_[a-z]+_[a-z]+_(df|full)$

# DWD Layer
^dwd_[a-z]+_[a-z]+_(di|df|hi)$

# DWM Layer
^dwm_[a-z]+_[a-z]+_[a-z]+_(di|df|nd)$

# DWS Layer
^dws_[a-z]+_[a-z]+_(1d|7d|30d|90d|nd)_(di|nd)$

# ADS Layer
^ads_[a-z]+_[a-z]+_(df|di|rt|full)$

12.2 CI/CD Integration

Example GitHub Actions validation:

name: Table Naming Validation
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Check table names
        run: |
          python validate_naming.py --files ${{ github.event.pull_request.files }}

13. QUICK REFERENCE CARD


| Layer       | Pattern                               | Example
| ------------| --------------------------------------| ------------
| ODS         | ods_{source}_{table}_{suffix}         | ods_mysql_order_di
| DIM         | dim_{domain}_{entity}_{suffix}        | dim_user_info_df
| DWD         | dwd_{domain}_{entity}_{suffix}        | dwd_trade_order_di
| DWM         | dwm_{domain}_{entity}_{proc}_{suffix} | dwm_order_merge_di
| DWS         | dws_{domain}_{entity}_{win}_{suffix}  | dws_user_7d_nd
| ADS         | ads_{app}_{metric}_{suffix}           | ads_exec_kpi_df

Suffix Meanings:
di: Daily Incremental
df: Daily Full Snapshot
hi: Hourly Incremental
hf: Hourly Full Snapshot
nd: N-Day Rolling
rt: Real-Time
full: Static Load

14. RELATED DOCUMENTS


- docs/layers/ODS_DESIGN.md - ODS layer specifications
- docs/layers/DWD_DESIGN.md - DWD layer specifications
- docs/layers/DWM_DESIGN.md - DWM layer specifications
- docs/layers/DWS_DESIGN.md - DWS layer specifications
- docs/layers/ADS_DESIGN.md - ADS layer specifications
- docs/standards/SQL_STANDARDS.md - SQL coding standards