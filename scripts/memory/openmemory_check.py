#!/usr/bin/env python3
"""Health check for the local OpenMemory (mem0) instance - `oi-openmemory-prod`.

Prints endpoint status only. The API key is read from the environment and sent
as a bearer token; its value is never printed. Exit code: 0 reachable, 1 not.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8760"


def _probe(url: str, api_key: str) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "clawteam-openmemory-check")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        # 401/403 still proves the service is up; auth config is a separate concern.
        return exc.code in (401, 403), f"HTTP {exc.code} (service up, auth challenged)"
    except Exception as exc:
        return False, type(exc).__name__


def main() -> int:
    base = os.environ.get("OPENMEMORY_BASE_URL", "").rstrip("/") or DEFAULT_BASE
    api_key = os.environ.get("OPENMEMORY_API_KEY", "")
    user = os.environ.get("OPENMEMORY_USER", "oi-openmemory-prod")

    print("OpenMemory profile : oi-openmemory-prod")
    print(f"Endpoint           : {base} (env OPENMEMORY_BASE_URL overrides)")
    print(f"MCP endpoint       : {base}/mcp")
    print(f"Auth               : OPENMEMORY_API_KEY {'SET (sent as bearer)' if api_key else 'NOT SET'}")
    print(f"Memory user        : {user}")

    ok_root, detail_root = _probe(base, api_key)
    ok_mcp, detail_mcp = _probe(f"{base}/mcp", api_key)
    print(f"GET /              : {detail_root}")
    print(f"GET /mcp           : {detail_mcp}")

    if ok_root or ok_mcp:
        print("STATUS: REACHABLE")
        return 0
    print("STATUS: UNREACHABLE - start the local OpenMemory stack or set OPENMEMORY_BASE_URL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
