"""Board-native bridge to the local IureOCR MCP server (Tesseract + pdfium).

Powers the Data Extraction panel (Extract view) through /api/ocr/* routes.
The server location is hardcoded to this machine's install target
(I:\\LocalApps\\IureOCR — app-owned, per the install-target policy);
CLAWTEAM_IUREOCR_EXE can override for dev/test. Transport is stdio
JSON-RPC (MCP): initialize -> tools/call, newline-delimited JSON.
Fully local: no network, no cloud, originals never modified.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any, Sequence

IUREOCR_EXE = Path(os.environ.get("CLAWTEAM_IUREOCR_EXE", r"I:\LocalApps\IureOCR\app\iureocr.exe"))
IUREOCR_ARGS: tuple[str, ...] = ("--mcp",)
_CALL_TIMEOUT = float(os.environ.get("CLAWTEAM_OCR_TIMEOUT", "600"))
_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class OcrBridgeError(RuntimeError):
    """Raised for anything the panel should surface as an error message."""


# --- hardcoded tool catalog (mirrors the IureOCR MCP schema) -----------------
# kinds: str | int | bool | enum | pages   (form strings are coerced)

_TOOL_SPECS: dict[str, dict[str, tuple[str, bool]]] = {
    "ocr_file": {
        "path": ("str", True),
        "languages": ("str", False),
        "force": ("bool", False),
        "output_dir": ("str", False),
        "include_text": ("bool", False),
        "max_chars": ("int", False),
    },
    "extract_text": {
        "path": ("str", True),
        "start_page": ("int", False),
        "end_page": ("int", False),
        "max_chars": ("int", False),
    },
    "pdf_info": {
        "path": ("str", True),
    },
    "render_page": {
        "path": ("str", True),
        "page": ("int", False),
        "width": ("int", False),
    },
    "edit_pdf_pages": {
        "path": ("str", True),
        "operation": ("enum", True),
        "pages": ("pages", True),
        "degrees": ("enum-int", False),
    },
    "ocr_languages": {},
}

_TOOL_SUMMARIES: dict[str, str] = {
    "ocr_file": (
        "Run OCR (Tesseract) on a scanned PDF or image. Writes a searchable PDF "
        "and .txt next to the original (original not modified) and returns the text."
    ),
    "extract_text": (
        "Read the text layer of a PDF by page range, or a .txt file. If pages have "
        "no text the PDF is a scan - use ocr_file."
    ),
    "pdf_info": (
        "Page count, page sizes and whether a PDF already has a text layer "
        "(that is: whether it needs OCR)."
    ),
    "render_page": (
        "One page of a PDF (or an image) as a JPEG - signatures, stamps, "
        "handwriting and layout that OCR text cannot capture."
    ),
    "edit_pdf_pages": (
        "Remove, keep, rotate or reorder pages of a PDF. Writes a new PDF next to "
        "the original; use it to chunk huge scans before OCR."
    ),
    "ocr_languages": (
        "Tesseract version and the OCR language packs installed on this machine."
    ),
}

_ENUM_OPERATIONS = {"delete", "keep", "rotate", "reorder"}
_ENUM_DEGREES = {90, 180, 270}


def tool_catalog() -> list[dict[str, Any]]:
    """The six hardcoded tools with their argument specs, for the panel/status."""
    catalog = []
    for name, params in _TOOL_SPECS.items():
        catalog.append({
            "name": name,
            "summary": _TOOL_SUMMARIES.get(name, ""),
            "arguments": [
                {"name": arg, "kind": kind, "required": required}
                for arg, (kind, required) in params.items()
            ],
        })
    return catalog


def server_status() -> dict[str, Any]:
    return {
        "exe": str(IUREOCR_EXE),
        "args": list(IUREOCR_ARGS),
        "available": IUREOCR_EXE.is_file(),
    }


# --- argument coercion ------------------------------------------------------


def build_arguments(tool: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    """Validate + coerce panel form values into MCP tool arguments."""
    if tool not in _TOOL_SPECS:
        raise OcrBridgeError(
            f"unknown tool: {tool!r} (expected one of {', '.join(_TOOL_SPECS)})"
        )
    specs = _TOOL_SPECS[tool]
    raw = raw or {}
    unknown = [k for k in raw if k not in specs]
    if unknown:
        raise OcrBridgeError(f"unknown argument(s) for {tool}: {', '.join(unknown)}")

    out: dict[str, Any] = {}
    for name, (kind, required) in specs.items():
        if name not in raw or raw[name] is None:
            if required:
                raise OcrBridgeError(f"{tool}: missing required argument '{name}'")
            continue
        value = raw[name]
        try:
            if kind == "str":
                coerced = str(value).strip()
                if not coerced:
                    if required:
                        raise OcrBridgeError(f"{tool}: '{name}' must not be empty")
                    continue
            elif kind == "int":
                coerced = int(str(value).strip())
            elif kind == "bool":
                if isinstance(value, str):
                    coerced = value.strip().lower() in {"1", "true", "yes", "on"}
                else:
                    coerced = bool(value)
            elif kind == "enum":
                coerced = str(value).strip().lower()
                if coerced not in _ENUM_OPERATIONS:
                    raise OcrBridgeError(
                        f"{tool}: operation must be one of {', '.join(sorted(_ENUM_OPERATIONS))}"
                    )
            elif kind == "enum-int":
                coerced = int(str(value).strip())
                if coerced not in _ENUM_DEGREES:
                    raise OcrBridgeError(
                        f"{tool}: degrees must be one of {', '.join(str(d) for d in sorted(_ENUM_DEGREES))}"
                    )
            elif kind == "pages":
                if isinstance(value, str):
                    value = [p.strip() for p in value.split(",") if p.strip()]
                coerced = [int(str(v).strip()) for v in value]
                if not coerced or any(p < 1 for p in coerced):
                    raise OcrBridgeError(f"{tool}: pages must be positive 1-based integers")
        except (TypeError, ValueError) as exc:
            raise OcrBridgeError(f"{tool}: invalid value for '{name}': {exc}") from exc
        out[name] = coerced
    return out


# --- MCP stdio client -------------------------------------------------------


class _McpStdioClient:
    """Minimal newline-delimited JSON-RPC client for a stdio MCP server."""

    def __init__(self, command: Sequence[str], timeout: float = _CALL_TIMEOUT):
        self._command = [str(part) for part in command]
        self._timeout = timeout
        self._proc: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str] = queue.Queue()
        self._next_id = 0

    def __enter__(self) -> "_McpStdioClient":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def start(self) -> dict[str, Any]:
        if self._proc is not None:
            raise OcrBridgeError("client already started")
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_CREATE_NO_WINDOW,
        )
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        try:
            return self.request("initialize", params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "clawteam-board", "version": "1.0"},
            })
        except Exception:
            self.close()  # never leak the child process on a failed handshake
            raise

    def _pump_stdout(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        for line in self._proc.stdout:
            self._lines.put(line)
        self._lines.put("")  # EOF sentinel: reader raises instead of blocking

    def _send(self, message: dict[str, Any]) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        try:
            self._proc.stdin.write(json.dumps(message) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise OcrBridgeError(f"MCP server pipe broken: {exc}") from exc

    def _read_message(self, want_id: int) -> dict[str, Any]:
        skipped: list[str] = []
        while True:
            try:
                line = self._lines.get(timeout=self._timeout)
            except queue.Empty:
                raise OcrBridgeError(
                    f"MCP server timed out after {self._timeout:.0f}s (no response id={want_id})"
                ) from None
            if not line:
                raise OcrBridgeError("MCP server closed its output pipe")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # non-JSON noise on stdout
            if not isinstance(message, dict):
                continue
            if message.get("id") == want_id:
                for saved in skipped:  # replay lines this call did not consume
                    self._lines.put(saved)
                return message
            skipped.append(line)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method,
                    "params": params or {}})
        response = self._read_message(request_id)
        if "error" in response:
            error = response["error"]
            detail = error.get("message", error) if isinstance(error, dict) else error
            raise OcrBridgeError(f"MCP error from {method}: {detail}")
        return response.get("result") or {}

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> list[Any]:
        if self._proc is None:
            raise OcrBridgeError("client not started")
        result = self.request("tools/call", params={"name": name, "arguments": arguments})
        content = result.get("content")
        if result.get("isError"):
            snippet = next((b.get("text", "") for b in content or []
                            if isinstance(b, dict) and b.get("type") == "text"), "")
            raise OcrBridgeError(f"{name} failed: {snippet[:400] or 'unknown tool error'}")
        return content if isinstance(content, list) else ([] if content is None else [content])

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin is not None:
                proc.stdin.close()
            proc.wait(timeout=3)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
            proc.wait(timeout=3)


# --- public bridge -----------------------------------------------------------

_LOCK = threading.Lock()  # one OCR pipeline at a time; Tesseract is CPU-heavy


def _normalize_blocks(blocks: Sequence[Any]) -> dict[str, Any]:
    texts: list[str] = []
    images: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            if isinstance(block, str):
                texts.append(block)
            continue
        block_type = block.get("type")
        if block_type == "text":
            texts.append(str(block.get("text", "")))
        elif block_type == "image":
            data = str(block.get("data", "")).strip()
            if data:
                images.append(f"data:{block.get('mimeType') or 'image/jpeg'};base64,{data}")
        elif block_type == "resource":
            resource = block.get("resource")
            if isinstance(resource, dict) and isinstance(resource.get("text"), str):
                texts.append(resource["text"])
    return {"text": "\n".join(texts), "images": images}


def _server_command() -> list[str]:
    return [str(IUREOCR_EXE), *IUREOCR_ARGS]


def call_tool(tool: str, arguments: dict[str, Any] | None,
              *, command: Sequence[str] | None = None) -> dict[str, Any]:
    """Call one hardcoded IureOCR tool; returns {'text': str, 'images': [data-uri]}."""
    args = build_arguments(tool, arguments)
    command = list(command) if command is not None else _server_command()
    with _LOCK:
        try:
            with _McpStdioClient(command) as client:
                client.notify("notifications/initialized")
                content = client.call_tool(tool, args)
        except OcrBridgeError:
            raise
        except FileNotFoundError as exc:
            raise OcrBridgeError(f"IureOCR MCP executable not found: {exc}") from exc
        except Exception as exc:  # unexpected spawn/pipe failures
            raise OcrBridgeError(f"IureOCR MCP call failed: {exc}") from exc
    return _normalize_blocks(content)
