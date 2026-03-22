# data-warehouse-modeling-skill
Agent skill for design and building layered data warehouse modeling.

This Data Modeling skill enables the design of structured, scalable, and efficient data schemas aligned with the layered data warehouse architecture (ODS, DWD, DWM, DWS, ADS). This skill translates business requirements into logical and physical data models, ensuring data integrity, query performance, and maintainability. It encompasses dimensional modeling, normalization, slowly changing dimension (SCD) strategies, and grain definition.

The skill ensures that all models adhere to the established naming conventions, layer responsibilities, and SQL standards defined in the architecture documentation. It bridges the gap between business needs and technical implementation by defining clear relationships, keys, and metrics.

## ACTIVATION COMMANDS:
  - "Activate data modeling Skill" - Enable this skill
  - "Design table for [requirement]" - Start table design workflow
  - "Generate DDL for [table_name]" - Generate CREATE TABLE statement
  - "Generate ETL for [source] -> [target]" - Generate transformation SQL
  - "Review data modeling architecture" - Audit existing table designs

## When to use this

Use this skill in the following scenarios:

1. Design data warehouse from scratch follow professional design principles and best practices.
2. Layered data modeling design leverage the medallion architecture, the Kimball architecture and Alibaba's OneData concept.
3. New Source Integration: When ingesting data from a new source system into the ODS layer.
4. Data model Improvemet: When exsiting model requires to split and move sql logic into different layers to improve the felxibility, maintainability, and performance.
5. Performance Optimization: When existing queries are slow due to poor schema design, requiring denormalization or aggregation strategies.
6. Schema Evolution: When source systems change structure, requiring updates to DWD/DIM tables and SCD handling.
7. New Analytics Requirements: When business stakeholders request new metrics, reports, or dashboards requiring new DWS or ADS tables.
8. Data Mart Creation: When building subject-area specific data marts for specific departments (Finance, Marketing, Operations).
9. Refactoring: When cleaning up technical debt, inconsistent metrics, or redundant tables in the warehouse.

## REFERENCE DOCUMENTS:

Always consult these documents when making design decisions:
  - docs/layers/ODS_DESIGN.md - ODS layer specifications
  - docs/layers/DWD_DESIGN.md - DWD layer specifications
  - docs/layers/DWM_DESIGN.md - DWM layer specifications
  - docs/layers/DWS_DESIGN.md - DWS layer specifications
  - docs/layers/ADS_DESIGN.md - ADS layer specifications
  - docs/standards/NAMING_CONVENTION.md - Naming standards
  - docs/standards/SQL_STANDARDS.md - SQL coding standards

CORE ARCHITECTURE STANDARDS:

  Layer Responsibilities:
  - ODS (ods_): Raw data ingestion, minimal cleaning. Preserve source structure. Partition by dt.
  - DIM (dim_): Conformed dimensions (Master Data). Handle SCD (Type 1/2). Source of truth for joins.
  - DWD (dwd_): Cleaned detail facts, standardized logic. Atomic granularity. Star schema.
  - DWM (dwm_): Mid-level aggregation, business logic application. Bridge between DWD and DWS.
  - DWS (dws_): Aggregated topic-wide tables. Pre-compute metrics (1d, 7d, 30d).
  - ADS (ads_): Application-specific data products. Optimized for BI/API/Reports.
