# Superkepler
<img width="1962" height="1206" alt="图片" src="https://github.com/user-attachments/assets/e439e93c-dd21-400b-a60b-fcbeb6ac6aeb" />
Superkepler is an advanced agent skill for data modeling, i.e. design and build layered data warehouse model. It is designed to transition data teams from the loose "Medallion" pattern to the flexible and extensible ODS-DWD-DWM-DWS-ADS kepler data architecture.

While many frameworks focus purely on data cleanliness, Superkepler focuses on data structure. It automates the creation of high-performance, layered data warehouses by applying the "Laws of Dimensional Motion" to your raw data sources.

Superkepler enables the design of structured, scalable, and efficient data schemas aligned with the layered data warehouse architecture (ODS, DWD, DWM, DWS, ADS), i.e. the kepler data architecture. This skill translates business requirements into logical and physical data models, ensuring data integrity, query performance, and maintainability. It encompasses dimensional modeling, normalization, slowly changing dimension (SCD) strategies, and grain definition.

The skill ensures that all models adhere to the established naming conventions, layer responsibilities, and SQL standards defined in the architecture documentation. It bridges the gap between business needs and technical implementation by defining clear relationships, keys, and metrics. 

## The Superkepler Story: What's in a Name?

In data engineering, names dictate philosophy. The popular Medallion Architecture (Bronze, Silver, Gold) focuses on data purity whivh is the idea that data simply gets cleaner as it moves through the pipeline. However, the Medallion pattern does not prescribe specific schema designs, data integration methods, or enterprise relationship models.

We chose the name Superkepler because modern, large-scale data ecosystems require more than just clean data. They require laws, structure, and predictable motion.

### The Star Connection 

In the 17th century, astronomer Johannes Kepler discovered the mathematical laws governing planetary motion, bringing geometric order to the seemingly chaotic movement of the stars.

The name **Superkepler** references Johannes Kepler’s laws of planetary motion, using it as a structural analogy for Kimball-style dimensional modeling (Star Schema). The naming convention reflects the systematic progression of data from operational source layers to clean and rational analytical structures.

Why Superkepler was Chosen for this Skill:

- Predictable Orbital Flow: Data modeling shouldn't be random or left to developer whim. Superkepler implies that your data pipelines follow an optimized, strictly governed path. Every table has a definitive "orbit" (layer) where it belongs.

- A Nod to the "Star" Schema: It is a deliberate, structural nod to Kimball-style dimensional modeling. While Medallion might result in flat, unstructured "Golden Swamps," Superkepler explicitly builds organized galaxies of Fact and Dimension tables.

- Enterprise Rigor with AI Velocity: Unlike generic SQL generation utilities, Superkepler stands out as an enterprise-grade agent skill. It signals to data architects that this agent skill doesn't just write code, it enforces elite data modeling architecture. By prioritizing a standardized, multi-layered schema design, Superkepler builds the core data foundation (clean and dimensionally modeled datasets) required to make downstream analytical, AI tools, and generic text-to-SQL agents effective.

## The Superkepler Strata

Superkepler organizes your data into four distinct, purposeful layers:

- ODS (Operational Data Store): The "Source of Truth." A 1:1 mirror of upstream systems with technical metadata, ensuring a reliable audit trail.

- DWD (Data Warehouse Detail): The "Atomic Layer." Data is cleaned, standardized, and deduplicated at the most granular level.

- DWM (Data Warehouse Middle): The "Common Orbit." This is where reusable business logic lives. DWM joins related atomic tables (e.g., Order + OrderItem) into common mid-level entities that serve multiple DWS summaries.

- DWS (Data Warehouse Summary): The "Star Schema." This is where high-performance Fact and Dimension tables are forged for reusable cross-domain analysis.

- ADS (Application Data Service): The "Consumption Layer." Purpose-built, denormalized views optimized for specific BI tools, APIs, and stakeholders.

## Why Superkepler?

**Beyond the Medallion - The Evolution of the Warehouse:**  
Medallion (Bronze/Silver/Gold) was great for simple pipelines, but it often lacks the dimensional extensibility needed for modern, large-scale analytics. Medallion was designed for the early days of Data Lakes. **Superkepler** is built for the Lakehouse era with professional data modeling at enerprise level.

Inspired by the methodologies that power Ant Group's and Alibaba's global ecosystem, Superkepler replaces the loose "Medallion" layers with a high-precision structure:

1. **Scale-Ready Logic:** Unlike the "Silver" and "Gold" layer, which often becomes a "Data Swamp," Superkepler's **DWD**, **DWM**, **DWW**, **ADS** layers enforce strict atomicity and reuse, a technique perfected in the *Data Middle Office* to handle billions of transactions.
2. **True Star Schemas:** By mandating a **DWS** layer, Superkepler ensures your warehouse isn't just a collection of "Clean Tables," but a functioning **Dimensional Model** optimized for high-speed queries.
3. **Decoupled Consumption:** The **ADS** layer ensures your raw warehouse logic never "leaks" into your BI tools, maintaining a clean separation of concerns.

## Architectural Rationale: Transitioning from Medallion

The Medallion architecture (Bronze, Silver, Gold) categorizes data by data quality states. While effective for basic data lakes, it introduces design limitations at enterprise scale:

| Architectural Challenge | Medallion (Bronze/Silver/Gold) | Superkepler |
| :--- | :--- | :--- |
| **Silver Layer Scope** | Overloaded with both data cleaning and complex business joins. | Decoupled into DWD (atomic cleaning) and DWM (reusable joins). |
| **Dimensional Modeling** | Optional or implicitly pushed to the Gold layer. | Enforced at the core via the DWS layer. |
| **Logic Redundancy** | High risk of logic duplication across downstream views. | Low; intermediate logic is centralized in the DWM layer. |
| **Downstream Performance** | Highly dependent on dynamic runtime execution paths. | Optimized through pre-calculated, flat schema definitions in the ADS layer. |

## ACTIVATION COMMANDS:
  - "Activate data modeling Skill" - Enable this skill
  - "Design table for [requirement]" - Start table design workflow
  - "Generate DDL for [table_name]" - Generate CREATE TABLE statement
  - "Generate ETL for [source] -> [target]" - Generate transformation SQL
  - "Review data modeling architecture" - Audit existing table designs

## When to use this

Use this skill in the following scenarios:

1. Design lakehouse or data warehouse from scratch follow professional design principles and best practices.
2. Layered data modeling design leverage the medallion architecture, the Kimball architecture.
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

You can integrate this skill into your Claude environment using the Makefile.

 1. **Clone the repository:**
    ```bash
    git clone https://github.com/JingGe/superkepler.git
    ```

Note: you can also download a release version and extract it.

 2. **Install the skill**
    ```bash
    cd <target_folder>/superkepler
    make install
    ```

Note: use `make unstill` to remove superkepler and use `make reinstall` to remove the old superkepler and then install current superkepler.

 3. **Activate the Skill:**

 Open a new Claude Code session and press / in your Claude TUI session. You should see the custom command registered in your namespace::

   ```bash
   /superkepler
   ```

### Usage

Once installed, Claude code will automatically leverage these instructions when you ask data-related questions. You can also trigger it explicitly:

 - Natural Language: "Using superkepler, design a star schema for a retail analytics dashboard."

 - Slash Command: /superkepler Create a DWD layer design for the given data source.

 - Slash only: /superkepler. Then you use natural language to ask the skill to design data modeling or generate SQL scripts


## Inspiration

**Superkepler** is an independent agent skill for the implementation of the **OneData** methodology, inspired by the architectural principles found in the book *The Big Data Road: Alibaba's Data Middle Office Practice*. 

While it honors the robust ODS-DWD-DWM-DWS-ADS layering used by global-scale data organizations, Superkepler is modernized for 2026 AI-driven workflows and remains an independent tool not affiliated with Ant Group, Alibaba Group, or NVIDIA Corporation.
