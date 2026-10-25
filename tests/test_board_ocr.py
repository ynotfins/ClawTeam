"""Tests for the board's hardcoded IureOCR MCP bridge (/api/ocr/* backing)."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from clawteam.board import ocr_tools
from clawteam.board import server as board_server

FAKE_MCP = textwrap.dedent("""
    import json
    import sys

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:
            continue
        if msg.get("method") == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {},
                      "serverInfo": {"name": "fake-iureocr", "version": "0"}}
        elif msg.get("method") == "tools/call":
            name = (msg.get("params") or {}).get("name", "")
            result = {"isError": False, "content": [
                {"type": "text", "text": "tool=" + name},
                {"type": "image", "data": "aGVsbG8=", "mimeType": "image/jpeg"},
            ]}
        else:
            result = {}
        sys.stdout.write(json.dumps(
            {"jsonrpc": "2.0", "id": msg["id"], "result": result}) + "\\n")
        sys.stdout.flush()
""")


@pytest.fixture()
def fake_mcp_command(tmp_path: Path) -> list[str]:
    script = tmp_path / "fake_mcp.py"
    script.write_text(FAKE_MCP, encoding="utf-8")
    return [sys.executable, str(script)]


def test_tool_catalog_lists_exactly_the_six_hardcoded_tools():
    catalog = ocr_tools.tool_catalog()
    names = [tool["name"] for tool in catalog]
    assert names == ["ocr_file", "extract_text", "pdf_info",
                     "render_page", "edit_pdf_pages", "ocr_languages"]
    by_name = {tool["name"]: tool for tool in catalog}
    assert by_name["ocr_file"]["summary"]
    ocr_file_args = {a["name"]: a for a in by_name["ocr_file"]["arguments"]}
    assert ocr_file_args["path"]["required"] is True
    assert ocr_file_args["languages"]["required"] is False
    assert by_name["ocr_languages"]["arguments"] == []
    edit_args = {a["name"]: a for a in by_name["edit_pdf_pages"]["arguments"]}
    assert edit_args["operation"]["kind"] == "enum"
    assert edit_args["pages"]["kind"] == "pages"
    assert edit_args["degrees"]["kind"] == "enum-int"


def test_build_arguments_coerces_forms():
    args = ocr_tools.build_arguments("edit_pdf_pages", {
        "path": " D:\\scan.pdf ",
        "operation": "Keep",
        "pages": "1, 2,3",
        "degrees": "180",
    })
    assert args == {"path": "D:\\scan.pdf", "operation": "keep",
                    "pages": [1, 2, 3], "degrees": 180}
    assert ocr_tools.build_arguments("ocr_file", {"path": "a.pdf", "force": "TRUE"})["force"] is True
    assert ocr_tools.build_arguments("ocr_file", {"path": "a.pdf", "max_chars": "500"})["max_chars"] == 500


@pytest.mark.parametrize("tool,arguments,needle", [
    ("nope", {}, "unknown tool"),
    ("ocr_file", {}, "missing required argument 'path'"),
    ("ocr_file", {"bogus": "1"}, "unknown argument"),
    ("edit_pdf_pages", {"path": "a.pdf", "operation": "shred"}, "operation must be one of"),
    ("edit_pdf_pages", {"path": "a.pdf", "operation": "keep", "pages": "0"}, "positive 1-based"),
])
def test_build_arguments_rejects_bad_input(tool, arguments, needle):
    with pytest.raises(ocr_tools.OcrBridgeError, match=needle):
        ocr_tools.build_arguments(tool, arguments)


def test_call_tool_against_fake_mcp_server(fake_mcp_command):
    result = ocr_tools.call_tool(
        "ocr_file", {"path": "synthetic.pdf", "max_chars": 1000},
        command=fake_mcp_command,
    )
    assert result == {
        "text": "tool=ocr_file",
        "images": ["data:image/jpeg;base64,aGVsbG8="],
    }


def test_call_tool_serializes_two_calls_over_one_client(fake_mcp_command):
    with ocr_tools._McpStdioClient(fake_mcp_command) as client:
        client.notify("notifications/initialized")
        first = client.call_tool("pdf_info", {"path": "a.pdf"})
        second = client.call_tool("ocr_languages", {})
        assert first == [
            {"type": "text", "text": "tool=pdf_info"},
            {"type": "image", "data": "aGVsbG8=", "mimeType": "image/jpeg"},
        ]
        assert second[0]["text"] == "tool=ocr_languages"


def test_call_tool_surfaces_pipe_close_as_bridge_error(tmp_path: Path):
    script = tmp_path / "dying_mcp.py"
    script.write_text("import sys\nsys.stdout.close()\n", encoding="utf-8")
    with pytest.raises(ocr_tools.OcrBridgeError):
        ocr_tools.call_tool("pdf_info", {"path": "a.pdf"},
                            command=[sys.executable, str(script)])


def test_call_tool_missing_binary_is_a_clean_bridge_error():
    with pytest.raises(ocr_tools.OcrBridgeError, match="not found|failed"):
        ocr_tools.call_tool("pdf_info", {"path": "a.pdf"},
                            command=[r"Z:\definitely\missing\iureocr.exe"])


def test_server_status_reflects_env_override(monkeypatch):
    monkeypatch.setattr(ocr_tools, "IUREOCR_EXE", Path(r"C:\nowhere\iureocr.exe"))
    status = ocr_tools.server_status()
    assert status["available"] is False
    assert status["exe"].endswith("iureocr.exe")
    assert status["args"] == ["--mcp"]


def test_board_server_imports_the_ocr_bridge():
    # The /api/ocr/tools + /api/ocr/call routes call into this module at request time.
    assert board_server.ocr_tools is ocr_tools


def test_create_no_window_flag_zero_on_posix(monkeypatch):
    monkeypatch.setattr(ocr_tools.os, "name", "posix")
    import importlib
    reloaded = importlib.reload(ocr_tools)
    assert reloaded._CREATE_NO_WINDOW == 0
    importlib.reload(ocr_tools)  # restore module state for other tests
