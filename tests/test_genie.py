# tests/test_genie.py
import configparser
import os
import pytest
from unittest.mock import patch, mock_open

CONFIG_CONTENT_FULL = """
[DEFAULT]
host = https://adb-123.azuredatabricks.net
token = dapiABCDEF
warehouse_id = abc123
"""

CONFIG_CONTENT_MISSING_WAREHOUSE = """
[DEFAULT]
host = https://adb-123.azuredatabricks.net
token = dapiABCDEF
"""

def test_load_config_returns_all_keys():
    from scripts.genie import load_config
    with patch("builtins.open", mock_open(read_data=CONFIG_CONTENT_FULL)):
        with patch("os.path.exists", return_value=True):
            cfg = load_config()
    assert cfg["host"] == "https://adb-123.azuredatabricks.net"
    assert cfg["token"] == "dapiABCDEF"
    assert cfg["warehouse_id"] == "abc123"

def test_load_config_missing_file_raises():
    from scripts.genie import load_config
    with patch("os.path.exists", return_value=False):
        with pytest.raises(SystemExit, match="~/.databrickscfg not found"):
            load_config()

def test_load_config_missing_token_raises():
    from scripts.genie import load_config
    with patch("builtins.open", mock_open(read_data="[DEFAULT]\nhost=https://x.net\n")):
        with patch("os.path.exists", return_value=True):
            with pytest.raises(SystemExit, match="Missing key 'token'"):
                load_config()

def test_load_config_missing_warehouse_ok_without_require():
    from scripts.genie import load_config
    with patch("builtins.open", mock_open(read_data=CONFIG_CONTENT_MISSING_WAREHOUSE)):
        with patch("os.path.exists", return_value=True):
            cfg = load_config(require_warehouse=False)
    assert cfg.get("warehouse_id") is None

def test_load_config_missing_warehouse_prompts_and_accepts_input():
    from scripts.genie import load_config
    with patch("builtins.open", mock_open(read_data=CONFIG_CONTENT_MISSING_WAREHOUSE)):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.input", return_value="warehouse-xyz"):
                cfg = load_config(require_warehouse=True)
    assert cfg["warehouse_id"] == "warehouse-xyz"

def test_load_config_missing_warehouse_empty_input_exits():
    from scripts.genie import load_config
    with patch("builtins.open", mock_open(read_data=CONFIG_CONTENT_MISSING_WAREHOUSE)):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.input", return_value=""):
                with pytest.raises(SystemExit, match="warehouse_id is required"):
                    load_config(require_warehouse=True)

def test_format_columns_flags_json_columns():
    from scripts.genie import format_columns
    columns = [
        {"name": "user_id", "type_text": "STRING", "nullable": True, "comment": "User identifier"},
        {"name": "event_payload", "type_text": "STRING", "nullable": True, "comment": "Raw event"},
        {"name": "order_data", "type_text": "STRING", "nullable": False, "comment": "Order JSON blob"},
        {"name": "amount", "type_text": "DECIMAL(18,2)", "nullable": False, "comment": "Total"},
    ]
    output = format_columns(columns)
    assert "event_payload" in output
    assert "[JSON?]" in output
    assert "order_data" in output
    assert "amount" in output
    lines = output.split("\n")
    amount_line = next(l for l in lines if "amount" in l)
    assert "[JSON?]" not in amount_line

def test_format_columns_empty():
    from scripts.genie import format_columns
    assert "No columns" in format_columns([])

def test_format_result_truncated_warning():
    from scripts.genie import format_result
    columns = ["id", "name"]
    rows = [["1", "Alice"], ["2", "Bob"]]
    output = format_result(columns, rows, truncated=True)
    assert "Alice" in output
    assert "truncated" in output.lower()

def test_format_result_no_truncation_warning_when_complete():
    from scripts.genie import format_result
    columns = ["id"]
    rows = [["42"]]
    output = format_result(columns, rows, truncated=False)
    assert "42" in output
    assert "truncated" not in output.lower()

def test_format_result_empty():
    from scripts.genie import format_result
    output = format_result([], [], truncated=False)
    assert "0 rows" in output.lower() or "no rows" in output.lower()


# --- cmd_ask tests covering the fixed attachments-based path ---

def _make_genie_msg(summary=None, sql=None, statement_id=None):
    """Build a mock GenieMessage with attachments."""
    from unittest.mock import MagicMock
    msg = MagicMock()
    attachments = []

    if summary:
        text_att = MagicMock()
        text_att.text.content = summary
        text_att.query = None
        attachments.append(text_att)

    if sql or statement_id:
        query_att = MagicMock()
        query_att.text = None
        query_att.query.query = sql
        query_att.query.statement_id = statement_id
        attachments.append(query_att)

    msg.attachments = attachments
    return msg


def test_cmd_ask_prints_summary_from_attachments(capsys):
    from unittest.mock import MagicMock, patch
    import argparse
    from scripts.genie import cmd_ask

    msg = _make_genie_msg(summary="Total orders: 42")
    args = argparse.Namespace(space_id="abc123", question="How many orders?")

    with patch("scripts.genie.load_config", return_value={"host": "https://x", "token": "t", "warehouse_id": None}):
        with patch("scripts.genie.WorkspaceClient") as MockClient:
            MockClient.return_value.genie.start_conversation_and_wait.return_value = msg
            cmd_ask(args)

    out = capsys.readouterr().out
    assert "Total orders: 42" in out
    assert "Genie Summary" in out


def test_cmd_ask_prints_sql_from_attachments(capsys):
    from unittest.mock import MagicMock, patch
    import argparse
    from scripts.genie import cmd_ask

    msg = _make_genie_msg(sql="SELECT COUNT(*) FROM orders", statement_id=None)
    # No statement_id → no results fetch
    msg.attachments[0].query.statement_id = None
    args = argparse.Namespace(space_id="abc123", question="Count orders")

    with patch("scripts.genie.load_config", return_value={"host": "https://x", "token": "t", "warehouse_id": None}):
        with patch("scripts.genie.WorkspaceClient") as MockClient:
            MockClient.return_value.genie.start_conversation_and_wait.return_value = msg
            cmd_ask(args)

    out = capsys.readouterr().out
    assert "SELECT COUNT(*)" in out
    assert "Generated SQL" in out


def test_cmd_ask_fetches_results_via_statement_id(capsys):
    from unittest.mock import MagicMock, patch
    import argparse
    from scripts.genie import cmd_ask

    msg = _make_genie_msg(sql="SELECT id FROM t", statement_id="stmt-001")
    args = argparse.Namespace(space_id="abc123", question="Show ids")

    col = MagicMock()
    col.name = "id"
    stmt_result = MagicMock()
    stmt_result.manifest.schema.columns = [col]
    stmt_result.manifest.truncated = False
    stmt_result.result.data_array = [["1"], ["2"]]

    with patch("scripts.genie.load_config", return_value={"host": "https://x", "token": "t", "warehouse_id": None}):
        with patch("scripts.genie.WorkspaceClient") as MockClient:
            client = MockClient.return_value
            client.genie.start_conversation_and_wait.return_value = msg
            client.statement_execution.get_statement.return_value = stmt_result
            cmd_ask(args)

    out = capsys.readouterr().out
    assert "Results" in out
    assert "1" in out and "2" in out
    client.statement_execution.get_statement.assert_called_once_with(statement_id="stmt-001")


def test_cmd_ask_no_statement_response_attribute_does_not_crash(capsys):
    """Regression: old code crashed when query_result.statement_response didn't exist."""
    from unittest.mock import MagicMock, patch
    import argparse
    from scripts.genie import cmd_ask

    msg = MagicMock()
    msg.attachments = []  # No attachments — minimal response
    args = argparse.Namespace(space_id="abc123", question="Anything")

    with patch("scripts.genie.load_config", return_value={"host": "https://x", "token": "t", "warehouse_id": None}):
        with patch("scripts.genie.WorkspaceClient") as MockClient:
            MockClient.return_value.genie.start_conversation_and_wait.return_value = msg
            cmd_ask(args)  # Must not raise

    out = capsys.readouterr().out
    assert "superkepler" in out
