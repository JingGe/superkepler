# data-warehouse-modeling-skill
Agent skill for data modeling, i.e. design and building layered data warehouse model.

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

## CORE ARCHITECTURE STANDARDS:

  Layer Responsibilities:
  - ODS (ods_): Raw data ingestion, minimal cleaning. Preserve source structure. Partition by dt.
  - DIM (dim_): Conformed dimensions (Master Data). Handle SCD (Type 1/2). Source of truth for joins.
  - DWD (dwd_): Cleaned detail facts, standardized logic. Atomic granularity. Star schema.
  - DWM (dwm_): Mid-level aggregation, business logic application. Bridge between DWD and DWS.
  - DWS (dws_): Aggregated topic-wide tables. Pre-compute metrics (1d, 7d, 30d).
  - ADS (ads_): Application-specific data products. Optimized for BI/API/Reports.

## Installation

You can integrate this skill into your Claude environment using one of the methods below.

### Method 1: Claude Code CLI (Recommended)
This is the fastest way to keep the skill updated via the command line.

1. **Add the repository as a marketplace:**
   ```bash
   claude plugin marketplace add JingGe/data-modeling
   ```

2. **Install the skill:**
   ```bash
   claude plugin install data-modeling@JingGe
   ```

### Method 2: /plugin in Claude Code  (Recommended)

To install a skill from a GitHub repo using the slash command, follow these steps:
 1. Add the Repository as a Marketplace

 Claude Code needs to index the repository first. Run this command inside your terminal session:
    ```bash
    /plugin marketplace add JingGe/data-modeling-skill
    ```

 2. Install the Skill

 Once added, you install the specific plugin from that marketplace:
Bash

    ```bash
    /plugin install data-modeling-skill@JingGe
    ```

 (The @JingGe suffix ensures you are pulling from the correct marketplace alias).

 3. Activate the Skill

 For the changes to take effect immediately without restarting the CLI:
Bash

    ```bash
    /reload-plugins
    ```

### Method 3: Manual Installation

If you prefer to manage the files locally:

 1. Clone the repository:
    ```bash
    git clone https://github.com/JingGe/data-modeling.git
    ```

 2. Move to your global skills directory:
    ```bash
    mkdir -p ~/.claude/skills/
    cp -r data-modeling-skill ~/.claude/skills/
    ```

### Usage

Once installed, Claude code will automatically leverage these instructions when you ask data-related questions. You can also trigger it explicitly:

 - Natural Language: "Using my data modeling skill, design a Snowflake schema for a retail analytics dashboard."

 - Slash Command: /data-modeling Create a DWD layer design for the given data source.

 - Slash only: /data-modeling. Then you use natural language to ask the skill to design data modeling or generate SQL scripts