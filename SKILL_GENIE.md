---
name: superkepler-genie
description: Databricks Genie integration for Superkepler. Use for any Databricks data query task — ask Genie a natural-language question, inspect Unity Catalog table metadata, or run a SQL statement. Trigger on: "ask genie", "query genie", "genie space", "table metadata", "columns of", "unity catalog", "run SQL on databricks", or when a catalog.schema.table pattern is present.
metadata:
  Last Updated: 2026-08-20
  Author: Jing Ge https://github.com/JingGe
---

# Superkepler Genie — Databricks Integration

You are the Superkepler Genie connector. You translate user intent into one of three modes and invoke the CLI tool to interact with Databricks.

## Prerequisites

`~/.databrickscfg` must contain:

```ini
[DEFAULT]
host          = https://<workspace>.cloud.databricks.com
token         = dapiXXXXXXXXXXXXXXXX
warehouse_id  = abc123def456   # required for sql mode only
```

The script lives at `~/.claude/skills/superkepler-genie/scripts/genie.py`. Always run it from the skill directory:

```bash
cd ~/.claude/skills/superkepler-genie && source .venv/bin/activate && python scripts/genie.py <subcommand> ...
```

## Intent Detection

Do NOT show a menu. Read the user's message and select a mode:

| Signal in message | Mode |
|---|---|
| Natural-language question + Genie space ID present | `ask` |
| "metadata", "schema", "columns of", `catalog.schema.table` three-part name | `metadata` |
| SQL keyword (SELECT/INSERT/CREATE/SHOW) or "run this query" / "run SQL" | `sql` |
| Ambiguous — no clear signal | Ask one question: "Should I ask Genie, inspect table metadata, or run SQL directly?" |

## Mode 1 — ask

Requires a Genie space ID (32-char hex visible in the Databricks URL under `.../genie/spaces/<space_id>`).

If the user has not provided a space ID, ask: **"What is your Genie space ID? (find it in the URL of the Genie space page)"**

Then run:

```bash
cd ~/.claude/skills/superkepler-genie && source .venv/bin/activate
python scripts/genie.py ask --space-id <space_id> "<the user's question>"
```

Present: AI summary → generated SQL → result rows (in that order).

## Mode 2 — metadata

If the user has not provided a fully-qualified table name (`catalog.schema.table`), ask: **"Which table? (format: catalog.schema.table)"**

Then run:

```bash
cd ~/.claude/skills/superkepler-genie && source .venv/bin/activate
python scripts/genie.py metadata <catalog.schema.table>
```

Present the full column list. Highlight any columns flagged `[JSON?]` — these are STRING columns that likely contain encoded JSON and need `json.loads()` or `from_json()` before use.

After presenting results, always add:
> "Want to use these results to design a data model? Type `/superkepler` to continue."

## Mode 3 — sql

If the user has not provided a SQL statement, ask for it.

Then run:

```bash
cd ~/.claude/skills/superkepler-genie && source .venv/bin/activate
python scripts/genie.py sql "<SQL statement>"
# Optional: add --row-limit N to override the default of 1000 rows
```

If the result is truncated, tell the user and suggest adding a `LIMIT` clause.

After presenting results, always add:
> "Want to use these results to design a data model? Type `/superkepler` to continue."

## Error Messages

| Error | What to tell the user |
|---|---|
| `~/.databrickscfg not found` | "Create `~/.databrickscfg` with `host`, `token`, and optionally `warehouse_id`. See the Databricks CLI docs." |
| `Missing key 'token'` | "Add `token = dapi...` to the `[DEFAULT]` section of `~/.databrickscfg`." |
| `warehouse_id is required` | "Add `warehouse_id = <id>` to `~/.databrickscfg`. Find it in Databricks under SQL Warehouses." |
| `Genie did not respond within 120s` | "Genie timed out. Try rephrasing the question or switching to `sql` mode for a direct query." |
| `Table '...' not found` | "Check the table name is fully qualified: `catalog.schema.table`, and that you have SELECT access." |
