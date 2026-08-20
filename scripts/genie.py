# scripts/genie.py
import argparse
import configparser
import datetime
import os
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState


def load_config(profile: str = "DEFAULT", require_warehouse: bool = True) -> dict:
    cfg_path = os.path.expanduser("~/.databrickscfg")
    if not os.path.exists(cfg_path):
        sys.exit("~/.databrickscfg not found. See https://docs.databricks.com/dev-tools/cli/index.html")

    parser = configparser.ConfigParser()
    # configparser requires a section header; DEFAULT is special
    with open(cfg_path) as f:
        content = f.read()
    # Wrap bare DEFAULT block so configparser reads it correctly
    parser.read_string("[_root_]\n" + content)

    section = "_root_"
    raw = dict(parser[section])

    for key in ("host", "token"):
        if key not in raw:
            sys.exit(f"Missing key '{key}' in profile [{profile}] of ~/.databrickscfg")

    if require_warehouse and "warehouse_id" not in raw:
        try:
            warehouse_id = input(
                "warehouse_id not found in ~/.databrickscfg.\n"
                "Enter your SQL warehouse ID (find it in Databricks under SQL Warehouses): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nAborted.")
        if not warehouse_id:
            sys.exit("warehouse_id is required for this mode.")
        raw["warehouse_id"] = warehouse_id

    return {
        "host": raw["host"].rstrip("/"),
        "token": raw["token"],
        "warehouse_id": raw.get("warehouse_id"),
    }


_JSON_SUFFIXES = ("_json", "_payload", "_data", "_blob", "_raw")


def format_columns(columns: list[dict]) -> str:
    if not columns:
        return "No columns found."
    header = f"{'Name':<40} {'Type':<25} {'Null':<6} Comment"
    separator = "-" * 100
    lines = [header, separator]
    for col in columns:
        name = col.get("name", "")
        type_text = col.get("type_text", "")
        nullable = "YES" if col.get("nullable", True) else "NO"
        comment = col.get("comment", "")
        json_flag = ""
        if type_text.upper() == "STRING":
            low = name.lower()
            if any(low.endswith(s) for s in _JSON_SUFFIXES) or "json" in comment.lower():
                json_flag = " [JSON?]"
        lines.append(f"{name:<40} {type_text:<25} {nullable:<6} {comment}{json_flag}")
    return "\n".join(lines)


def cmd_metadata(args) -> None:
    cfg = load_config(require_warehouse=False)
    w = WorkspaceClient(host=cfg["host"], token=cfg["token"])
    try:
        table_info = w.tables.get(full_name=args.table)
    except Exception as e:
        sys.exit(f"Table '{args.table}' not found in Unity Catalog.\nDetail: {e}")

    columns = [
        {
            "name": col.name,
            "type_text": col.type_text or "",
            "nullable": col.nullable if col.nullable is not None else True,
            "comment": col.comment or "",
        }
        for col in (table_info.columns or [])
    ]

    print(f"\nTable: {args.table}")
    print(f"Comment: {table_info.comment or '(none)'}")
    print(f"Type: {table_info.table_type}\n")
    print(format_columns(columns))
    print(
        "\nWant to use these results to design a data model? Type `/superkepler` to continue."
    )


def format_result(columns: list[str], rows: list[list], truncated: bool) -> str:
    if not columns:
        return "No rows returned."
    col_widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(columns)]
    header = "  ".join(c.ljust(col_widths[i]) for i, c in enumerate(columns))
    separator = "  ".join("-" * col_widths[i] for i in range(len(columns)))
    lines = [header, separator]
    for row in rows:
        lines.append("  ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(columns))))
    lines.append(f"\n{len(rows)} row(s) returned.")
    if truncated:
        lines.append(
            "Result truncated. Add a LIMIT clause or pass --row-limit to see fewer rows."
        )
    return "\n".join(lines)


def cmd_sql(args) -> None:
    cfg = load_config(require_warehouse=True)
    w = WorkspaceClient(host=cfg["host"], token=cfg["token"])

    response = w.statement_execution.execute_statement(
        statement=args.statement,
        warehouse_id=cfg["warehouse_id"],
        row_limit=args.row_limit,
        wait_timeout="50s",
    )

    if response.status.state == StatementState.FAILED:
        sys.exit(
            f"SQL execution failed: {response.status.error.message}"
        )

    manifest = response.manifest
    result = response.result
    columns = [col.name for col in (manifest.schema.columns if manifest and manifest.schema else [])]
    rows = [list(row) for row in (result.data_array or [])] if result else []
    truncated = bool(manifest.truncated) if manifest else False

    print(format_result(columns, rows, truncated))
    print("\nWant to use these results to design a data model? Type `/superkepler` to continue.")


def cmd_ask(args) -> None:
    cfg = load_config(require_warehouse=False)
    w = WorkspaceClient(host=cfg["host"], token=cfg["token"])

    print(f"Asking Genie (space: {args.space_id})…\n")
    try:
        msg = w.genie.start_conversation_and_wait(
            space_id=args.space_id,
            content=args.question,
            timeout=datetime.timedelta(seconds=120),
        )
    except Exception as e:
        sys.exit(f"Genie did not respond: {e}\nTry again or use the `sql` subcommand.")

    if msg.content:
        print("=== Genie Summary ===")
        print(msg.content)

    if msg.query_result and msg.query_result.statement_response:
        stmt = msg.query_result.statement_response
        if stmt.statement:
            print("\n=== Generated SQL ===")
            print(stmt.statement)
        manifest = stmt.manifest
        result = stmt.result
        columns = [col.name for col in (manifest.schema.columns if manifest and manifest.schema else [])]
        rows = [list(row) for row in (result.data_array or [])] if result else []
        truncated = bool(manifest.truncated) if manifest else False
        if columns:
            print("\n=== Results ===")
            print(format_result(columns, rows, truncated))

    print("\nWant to use these results to design a data model? Type `/superkepler` to continue.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="superkepler-genie",
        description="Talk to Databricks Genie, Unity Catalog, and SQL execution.",
    )
    parser.add_argument("--profile", default="DEFAULT", help="~/.databrickscfg profile name")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ask = sub.add_parser("ask", help="Ask Genie a natural-language question")
    p_ask.add_argument("--space-id", required=True, help="Genie space ID (32-char hex)")
    p_ask.add_argument("question", help="Natural-language question")
    p_ask.set_defaults(func=cmd_ask)

    p_meta = sub.add_parser("metadata", help="Get column metadata for a Unity Catalog table")
    p_meta.add_argument("table", help="catalog.schema.table")
    p_meta.set_defaults(func=cmd_metadata)

    p_sql = sub.add_parser("sql", help="Execute a raw SQL statement")
    p_sql.add_argument("statement", help="SQL statement to execute")
    p_sql.add_argument("--row-limit", type=int, default=1000, help="Max rows to return (default 1000)")
    p_sql.set_defaults(func=cmd_sql)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
