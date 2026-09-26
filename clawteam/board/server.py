"""Lightweight HTTP server for the Web UI dashboard (stdlib only)."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from clawteam.board.collector import BoardCollector

_STATIC_DIR = Path(__file__).parent / "static"
_ALLOWED_PROXY_HOSTS = {
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
}

# Tools panel locations: the repo config is canonical for interactive sessions,
# the worker config governs spawned swarm agents. Writes go to both so every
# surface sees the same MCP servers and skills.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_REPO_FILE = _REPO_ROOT / ".mcp.json"
_WORKER_CONFIG = _REPO_ROOT / ".clawteam-local" / "claude-config" / ".claude.json"
_SKILL_ROOTS = {
    "repo": _REPO_ROOT / ".claude" / "skills",
    "worker": _REPO_ROOT / ".clawteam-local" / "claude-config" / "skills",
    "user": Path.home() / ".claude" / "skills",
}
_SWARM_CONFIG = Path.home() / ".clawteam" / "config.json"

# Theme payload served to the Web UI: the board's domain layer on top of RGDS
# (mode metadata + alias references + board-specific sizes — no color values).
# Colors themselves come from the vendored RGDS tokens.css in static/rgds/.
# Cached per mtime so edits appear on refresh without restart.
_theme_cache: dict[str, object] = {"mtime": 0.0, "body": b"{}"}


def _theme_file() -> Path:
    override = os.environ.get("CLAWTEAM_THEME_FILE", "")
    if override:
        return Path(override)
    from clawteam.team.models import get_data_dir

    return get_data_dir() / "theme.json"


def _load_theme_payload() -> dict:
    path = _theme_file()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    if mtime != _theme_cache["mtime"]:
        try:
            _theme_cache["body"] = path.read_bytes()
            _theme_cache["mtime"] = mtime
        except OSError:
            return {}
    try:
        payload = json.loads(_theme_cache["body"].decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects for proxied fetches."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(newurl, code, msg, headers, fp)


def _is_blocked_hostname(hostname: str) -> bool:
    host = hostname.strip().lower()
    if host in {"localhost"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
    )


def _normalize_proxy_target(target_url: str) -> str:
    parsed = urlparse(target_url)
    if parsed.scheme != "https":
        raise ValueError("Proxy only allows https URLs")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("Proxy URL must include a hostname")
    if _is_blocked_hostname(hostname):
        raise ValueError("Proxy target is not allowed")

    if hostname == "github.com":
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) == 2:
            return f"https://api.github.com/repos/{parts[0]}/{parts[1]}/readme"
        return target_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

    if hostname not in _ALLOWED_PROXY_HOSTS:
        raise ValueError("Proxy only allows GitHub-hosted content")

    return target_url


def _fetch_proxy_content(target_url: str) -> bytes:
    normalized = _normalize_proxy_target(target_url)
    opener = urllib.request.build_opener(_NoRedirectHandler)
    req = urllib.request.Request(normalized, headers={"User-Agent": "ClawTeam-Server"})
    with opener.open(req, timeout=10) as resp:
        final_url = resp.geturl()
        _normalize_proxy_target(final_url)
        body = resp.read()

    if normalized.startswith("https://api.github.com/repos/") and final_url == normalized:
        payload = json.loads(body.decode("utf-8"))
        download_url = payload.get("download_url")
        if not download_url:
            raise ValueError("GitHub README proxy target has no downloadable content")
        normalized = _normalize_proxy_target(download_url)
        req = urllib.request.Request(normalized, headers={"User-Agent": "ClawTeam-Server"})
        with opener.open(req, timeout=10) as resp:
            _normalize_proxy_target(resp.geturl())
            return resp.read()

    return body


@dataclass
class TeamSnapshotCache:
    """Tiny TTL cache for full team snapshots shared across HTTP handlers."""

    ttl_seconds: float
    _entries: dict[str, tuple[float, dict]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get(self, team_name: str, loader) -> dict:
        with self._lock:
            entry = self._entries.get(team_name)
            if entry and time.monotonic() - entry[0] < self.ttl_seconds:
                return entry[1]

        # Load outside the lock so one slow collector run does not block all
        # other readers. Concurrent expiry can trigger duplicate refreshes, but
        # this path only rebuilds an in-memory snapshot and the latest result wins.
        data = loader()
        loaded_at = time.monotonic()
        with self._lock:
            self._entries[team_name] = (loaded_at, data)
        return data


def _expand_env(value):
    """Expand ${VAR} references from the environment, recursively."""
    if isinstance(value, str):
        return re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _mcp_load() -> dict:
    return _read_json(_MCP_REPO_FILE, {}).get("mcpServers", {})


def _mcp_save(servers: dict) -> None:
    repo = _read_json(_MCP_REPO_FILE, {})
    repo["mcpServers"] = servers
    _write_json_atomic(_MCP_REPO_FILE, repo)
    worker = _read_json(_WORKER_CONFIG, {})
    worker["mcpServers"] = {k: dict(v) for k, v in servers.items()}
    _write_json_atomic(_WORKER_CONFIG, worker)


def _mcp_add(name: str, config: dict) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", name or ""):
        raise ValueError("name must be lowercase letters/digits/hyphens (max 40)")
    server_type = config.get("type")
    if server_type == "http":
        url = str(config.get("url", ""))
        if not url.startswith(("http://127.0.0.1", "http://localhost", "https://")):
            raise ValueError("http servers must use https or loopback http")
    elif server_type == "stdio":
        if not config.get("command"):
            raise ValueError("stdio servers require 'command'")
    else:
        raise ValueError("type must be 'http' or 'stdio'")
    servers = _mcp_load()
    servers[name] = config
    _mcp_save(servers)
    return {"status": "ok", "name": name}


def _mcp_remove(name: str) -> dict:
    servers = _mcp_load()
    if name not in servers:
        raise ValueError(f"unknown MCP server: {name}")
    del servers[name]
    _mcp_save(servers)
    return {"status": "ok", "removed": name}


def _mcp_test(name: str) -> dict:
    servers = _mcp_load()
    config = _expand_env(servers.get(name))
    if config is None:
        raise ValueError(f"unknown MCP server: {name}")
    if config.get("type") != "http":
        return {"ok": None, "note": "stdio server - verify with: claude mcp list"}
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "clawteam-board", "version": "1.0"}},
    }).encode("utf-8")
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    for k, v in (config.get("headers") or {}).items():
        headers[k] = str(v)
    req = urllib.request.Request(str(config["url"]), data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"ok": resp.status == 200, "http_status": resp.status}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http_status": e.code, "error": str(e.reason)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _parse_skill_frontmatter(text: str) -> tuple[str, str]:
    name, description = "", ""
    if text.startswith("---"):
        for line in text.split("---", 2)[1].splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip().lower(), value.strip()
            if key == "name" and not name:
                name = value
            elif key == "description" and not description:
                description = value
    return name, description


def _skills_list() -> list:
    found: dict[str, dict] = {}
    for scope, root in _SKILL_ROOTS.items():
        try:
            entries = sorted(root.iterdir())
        except OSError:
            continue
        for entry in entries:
            skill_file = entry / "SKILL.md"
            if not entry.is_dir() or not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            fm_name, fm_desc = _parse_skill_frontmatter(text)
            item = found.setdefault(entry.name, {"name": entry.name, "description": "", "scopes": []})
            item["scopes"].append(scope)
            if fm_desc and not item["description"]:
                item["description"] = fm_desc
            if fm_name and not item.get("fm_name"):
                item["fm_name"] = fm_name
    return list(found.values())


def _skill_add(name: str, description: str, content: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,39}", name or ""):
        raise ValueError("name must be lowercase letters/digits/hyphens (2-40)")
    if not content.strip():
        raise ValueError("content required")
    body = content if content.startswith("---") else (
        f"---\nname: {name}\ndescription: {description or name}\n---\n\n{content}"
    )
    written = []
    for scope, root in _SKILL_ROOTS.items():
        target = root / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(body, encoding="utf-8")
        written.append(scope)
    return {"status": "ok", "name": name, "scopes": written}


def _skill_remove(name: str) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,39}", name or ""):
        raise ValueError("invalid skill name")
    import shutil

    removed = []
    for scope, root in _SKILL_ROOTS.items():
        target = root / name
        if target.is_dir() and (target / "SKILL.md").exists():
            shutil.rmtree(target)
            removed.append(scope)
    if not removed:
        raise ValueError(f"unknown skill: {name}")
    return {"status": "ok", "removed": removed}


def _profiles_list() -> dict:
    cfg = _read_json(_SWARM_CONFIG, {})
    profiles = []
    for pname, p in (cfg.get("profiles") or {}).items():
        profiles.append({
            "name": pname,
            "description": p.get("description", ""),
            "agent": p.get("agent", ""),
            "model": p.get("model", ""),
            "default": pname == cfg.get("default_profile"),
        })
    return {"default_profile": cfg.get("default_profile", ""), "profiles": profiles}


# ---------------------------------------------------------------------------
# OpenRouter integration (board-native; key from User-scope env only)
# ---------------------------------------------------------------------------

_OR_BASE = "https://openrouter.ai"
_OR_MODELS_CACHE: dict[str, object] = {"expires": 0.0, "models": []}
_ROUTING_FILE = Path.home() / ".clawteam" / "openrouter_routing.json"
_ROUTING_ROLES = {
    "primary": "Main coding/reasoning model for every spawned agent",
    "small_fast": "Cheap+fast lane (classification, summaries, title gen)",
    "fallback": "Used when the primary provider errors or rate-limits",
    "vision": "Multimodal tasks: screenshots, images, UI dumps",
    "deep_reasoning": "Hard planning/architecture turns where latency is acceptable",
    "image_gen": "Image generation — local GPU via ComfyUI bridge (free); OpenRouter image models only as cloud fallback",
}


def _or_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def _or_fetch(path: str, auth: bool = True, timeout: int = 15) -> dict:
    headers = {"Content-Type": "application/json",
               "Accept": "application/json",
               "User-Agent": "ClawTeam-Board"}
    if auth:
        key = _or_key()
        if not key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(_OR_BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _or_models() -> list:
    now = time.time()
    if now < _OR_MODELS_CACHE["expires"]:
        return _OR_MODELS_CACHE["models"]
    raw = _or_fetch("/api/v1/models", auth=False)["data"]
    models = []
    for m in raw:
        pricing = m.get("pricing") or {}
        def per_m(v):
            try:
                return round(float(v) * 1_000_000, 4)
            except (TypeError, ValueError):
                return None
        arch = m.get("architecture") or {}
        models.append({
            "id": m.get("id", ""),
            "name": m.get("name", m.get("id", "")),
            "context_length": m.get("context_length"),
            "created": m.get("created"),
            "modality": arch.get("output_modality") or arch.get("input_modalities"),
            "prompt_per_m": per_m(pricing.get("prompt")),
            "completion_per_m": per_m(pricing.get("completion")),
            "cached_read_per_m": per_m(pricing.get("input_cache_read")),
            "cache_write_per_m": per_m(pricing.get("input_cache_write")),
            "free": str(pricing.get("prompt")) == "0" and str(pricing.get("completion")) == "0",
        })
    models.sort(key=lambda x: x["id"])
    _OR_MODELS_CACHE["expires"] = now + 600
    _OR_MODELS_CACHE["models"] = models
    return models


def _or_rankings(dataset: str, days: int = 7, limit: int = 20) -> dict:
    if dataset not in {"tools", "images"}:
        raise ValueError("dataset must be 'tools' or 'images' (OpenRouter live sets)")
    data = _or_fetch(f"/api/frontend/v1/rankings/{dataset}", auth=False)["data"]
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    totals: dict[str, float] = {}
    for point in data:
        if str(point.get("x", "")) < cutoff:
            continue
        for model_id, tokens in point.get("ys", {}).items():
            if model_id == "Others":
                continue
            try:
                totals[model_id] = totals.get(model_id, 0.0) + float(tokens)
            except (TypeError, ValueError):
                continue
    meta = {m["id"]: m for m in _or_models()}
    meta_by_prefix = {}
    for m in _or_models():
        base = re.sub(r"-\d{8}$", "", m["id"])
        meta_by_prefix.setdefault(base, m)

    def lookup(model_id):
        m = meta.get(model_id)
        if m:
            return m
        return meta_by_prefix.get(re.sub(r"-\d{8}$", "", model_id), {})

    rows = []
    for model_id, tokens in sorted(totals.items(), key=lambda kv: -kv[1])[:limit]:
        m = lookup(model_id)
        rows.append({
            "model": model_id,
            "name": m.get("name", model_id),
            "tokens_7d": round(tokens),
            "tokens_7d_m": round(tokens / 1_000_000, 1),
            "prompt_per_m": m.get("prompt_per_m"),
            "context_length": m.get("context_length"),
        })
    return {"dataset": dataset, "days": days, "rows": rows}


def _or_key_stats() -> dict:
    key = _or_fetch("/api/v1/auth/key")["data"]
    credits = _or_fetch("/api/v1/credits")["data"]
    return {
        "label": key.get("label", ""),
        "usage": key.get("usage"),
        "usage_daily": key.get("usage_daily"),
        "usage_weekly": key.get("usage_weekly"),
        "usage_monthly": key.get("usage_monthly"),
        "limit": key.get("limit"),
        "limit_remaining": key.get("limit_remaining"),
        "limit_reset": key.get("limit_reset"),
        "total_credits": credits.get("total_credits"),
        "total_usage": credits.get("total_usage"),
    }


def _routing_load() -> dict:
    routing = _read_json(_ROUTING_FILE, None)
    if not isinstance(routing, dict) or "roles" not in routing:
        profiles = _profiles_list()["profiles"]
        default_model = "z-ai/glm-5.3"
        for p in profiles:
            if p.get("default") and p.get("model"):
                default_model = p["model"]
        routing = {"roles": {
            "primary": default_model,
            "small_fast": "z-ai/glm-5.3-flash",
            "fallback": "deepseek/deepseek-v4-pro-0813",
            "vision": "minimax/minimax-m3",
            "deep_reasoning": "deepseek/deepseek-v4-pro-0813",
            "image_gen": "comfyui:RealVisXL_V5.0_fp16.safetensors",
        }}
    return routing


def _routing_apply(routing: dict) -> dict:
    """Persist the routing table and apply the primary/small lanes to the
    swarm's default openrouter profile so spawned agents follow it."""
    roles = routing.get("roles") or {}
    cfg = _read_json(_SWARM_CONFIG, {})
    default_profile = cfg.get("default_profile", "")
    profile = (cfg.get("profiles") or {}).get(default_profile)
    applied = {"saved_routing": True, "profile_updated": False}
    if profile and profile.get("base_url_env") == "ANTHROPIC_BASE_URL":
        env = profile.setdefault("env", {})
        if roles.get("primary"):
            profile["model"] = roles["primary"]
            env["ANTHROPIC_MODEL"] = roles["primary"]
        if roles.get("small_fast"):
            env["ANTHROPIC_SMALL_FAST_MODEL"] = roles["small_fast"]
        _write_json_atomic(_SWARM_CONFIG, cfg)
        applied["profile_updated"] = True
        applied["profile"] = default_profile
    _write_json_atomic(_ROUTING_FILE, routing)
    return applied


def _or_cache_lab(prompt: str, model: str) -> dict:
    if not prompt.strip():
        raise ValueError("prompt required")
    if not model:
        model = _routing_load()["roles"].get("primary", "z-ai/glm-5.3")
    session = f"clawteam-cache-lab-{int(time.time())}"
    runs = []
    for attempt in (1, 2):
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are the ClawTeam cache lab. Answer with one short sentence."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 40,
            "session_id": session,
        }).encode("utf-8")
        req = urllib.request.Request(
            _OR_BASE + "/api/v1/chat/completions", data=body, method="POST",
            headers={"Authorization": f"Bearer {_or_key()}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        usage = payload.get("usage") or {}
        details = usage.get("prompt_tokens_details") or {}
        cost = (usage.get("cost") or 0)
        runs.append({
            "run": attempt,
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cached_tokens": details.get("cached_tokens", 0),
            "cost": cost,
        })
    return {"model": model, "runs": runs,
            "cache_hit_second_run": (runs[1]["cached_tokens"] or 0) > 0}


class BoardHandler(BaseHTTPRequestHandler):
    """HTTP handler for the board Web UI."""

    collector: BoardCollector
    default_team: str = ""
    interval: float = 2.0
    team_cache: TeamSnapshotCache
    media_router: "object | None" = None
    upload_store: "object | None" = None

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            self._serve_static("index.html", "text/html")
        elif path == "/favicon.ico":
            self._serve_static("favicon.ico", "image/x-icon")
        elif path.startswith("/rgds/"):
            self._serve_rgds_asset(path)
        elif path == "/api/overview":
            self._serve_json(self.collector.collect_overview())
        elif path == "/api/theme":
            self._serve_json(_load_theme_payload())
        elif path == "/api/tools/mcp":
            self._serve_json({"servers": _mcp_load()})
        elif path == "/api/tools/skills":
            self._serve_json({"skills": _skills_list()})
        elif path == "/api/tools/profiles":
            self._serve_json(_profiles_list())
        elif path == "/api/openrouter/models":
            self._serve_json({"models": _or_models()})
        elif path == "/api/openrouter/rankings":
            query = parse_qs(urlparse(self.path).query)
            dataset = query.get("dataset", ["tools"])[0]
            days = int(query.get("days", ["7"])[0])
            self._serve_json(_or_rankings(dataset, days))
        elif path == "/api/openrouter/key":
            self._serve_json(_or_key_stats())
        elif path == "/api/openrouter/routing":
            routing = _routing_load()
            self._serve_json({"routing": routing, "role_docs": _ROUTING_ROLES})
        elif path == "/api/media/providers" and self.media_router:
            self._serve_json(self.media_router.providers_status())
        elif path == "/api/media/jobs" and self.media_router:
            query = parse_qs(urlparse(self.path).query)
            self._serve_json({"jobs": self.media_router.jobs.list(limit=int(query.get("limit", ["100"])[0]))})
        elif path.startswith("/api/media/jobs/") and self.media_router:
            job_id = path[len("/api/media/jobs/"):].strip("/").split("/")[0]
            job = self.media_router.jobs.get(job_id)
            if job is None:
                self.send_error(404, "unknown job")
            else:
                self._serve_json(job)
        elif path == "/api/media/assets" and self.media_router:
            self._serve_json({"assets": self.media_router.assets.list()})
        elif path == "/api/media/characters" and self.media_router:
            from clawteam.media.characters import CharacterStore
            self._serve_json({"characters": CharacterStore().list()})
        elif path == "/api/media/uploads" and self.upload_store:
            self._serve_json({"uploads": self.upload_store.list()})
        elif path.startswith("/api/media/uploads/") and path.endswith("/file") and self.upload_store:
            token = path[len("/api/media/uploads/"):][:-len("/file")]
            hit = self.upload_store.read_bytes(token)
            if hit is None:
                self.send_error(404, "unknown or expired upload")
                return
            record, data = hit
            self.send_response(200)
            self.send_header("Content-Type", record.get("mime", "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=60")
            self.end_headers()
            self.wfile.write(data)
        elif path.startswith("/api/media/assets/") and path.endswith("/file") and self.media_router:
            asset_id = path[len("/api/media/assets/"):][:-len("/file")]
            record = self.media_router.assets.get(asset_id)
            data = self.media_router.assets.read_bytes(asset_id) if record else None
            if record is None or data is None:
                self.send_error(404, "unknown asset")
                return
            self.send_response(200)
            self.send_header("Content-Type", record.get("mime", "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(data)
        elif path.startswith("/api/team/"):
            team_name = path[len("/api/team/"):].strip("/")
            if not team_name:
                self.send_error(400, "Team name required")
                return
            self._serve_team(team_name)
        elif path.startswith("/api/events/"):
            team_name = path[len("/api/events/"):].strip("/")
            if not team_name:
                self.send_error(400, "Team name required")
                return
            self._serve_sse(team_name)
        elif path.startswith("/api/proxy"):
            query = parse_qs(urlparse(self.path).query)
            target_url = query.get("url", [""])[0]
            if not target_url:
                self.send_error(400, "URL required")
                return
            try:
                content = _fetch_proxy_content(target_url)
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            except ValueError as e:
                self.send_error(403, str(e))
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]

        if path in ("/api/tools/mcp", "/api/tools/skills"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception as e:
                self.send_error(400, f"invalid JSON: {e}")
                return
            handler = _mcp_add
            action = payload.get("action", "add")
            try:
                if path == "/api/tools/mcp":
                    if action == "add":
                        result = _mcp_add(payload.get("name", ""), payload.get("config", {}))
                    elif action == "remove":
                        result = _mcp_remove(payload.get("name", ""))
                    elif action == "test":
                        result = _mcp_test(payload.get("name", ""))
                    else:
                        raise ValueError("action must be add|remove|test")
                else:
                    if action == "add":
                        result = _skill_add(payload.get("name", ""), payload.get("description", ""), payload.get("content", ""))
                    elif action == "remove":
                        result = _skill_remove(payload.get("name", ""))
                    else:
                        raise ValueError("action must be add|remove")
            except ValueError as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            except Exception as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            self._serve_json(result)
            return

        if path == "/api/media/uploads":
            # Raw binary image body (?filename=photo.jpg); NOT the JSON media API.
            from clawteam.media.uploads import ALLOWED_EXT, MAX_UPLOAD_BYTES, UploadStore
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                self._serve_json({"status": "error", "error": "empty upload"})
                return
            if content_length > MAX_UPLOAD_BYTES:
                self._serve_json({"status": "error",
                                  "error": f"upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB cap"})
                return
            ext = Path((parse_qs(urlparse(self.path).query).get("filename", [""])[0] or "")).suffix.lower()
            if ext not in ALLOWED_EXT:
                self._serve_json({"status": "error",
                                  "error": f"unsupported image type {ext or '(none)'} "
                                           f"(allowed: {', '.join(sorted(ALLOWED_EXT))})"})
                return
            body = self.rfile.read(content_length)
            try:
                record = UploadStore().save(body, ext=ext,
                                            original_name=parse_qs(urlparse(self.path).query)
                                            .get("filename", [""])[0])
            except ValueError as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            if record.get("url") is None:
                self._serve_json({"status": "error",
                                  "error": "photo saved locally, but no public origin is configured "
                                           "(media/photohost.json public_origin)"})
                return
            self._serve_json({"status": "ok", "upload": record})
            return

        if path.startswith("/api/media/") and self.media_router:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except Exception as e:
                self.send_error(400, f"invalid JSON: {e}")
                return
            router = self.media_router
            try:
                if path == "/api/media/jobs":
                    from clawteam.media.characters import CharacterStore
                    if payload.get("kind") == "variant":
                        cid = (payload.get("params") or {}).get("character_id") or ""
                        rec = CharacterStore().get(cid)
                        if rec is None or not rec.get("canonical_url"):
                            self._serve_json({"status": "error",
                                              "error": "pick a character with a finished canonical image first"})
                            return
                        ask = (payload.get("prompt") or "").strip() or "a friendly new pose"
                        payload["prompt"] = ("Same character - keep the face, hair, and identity "
                                             "exactly consistent with the reference. Now: " + ask)
                    if payload.get("kind") == "character":
                        src = (payload.get("params") or {}).get("source_url") or ""
                        if not src.startswith("https://"):
                            self._serve_json({"status": "error",
                                              "error": "photo link must be a public https URL"})
                            return
                        if not (payload.get("params") or {}).get("name"):
                            self._serve_json({"status": "error", "error": "character name required"})
                            return
                    job = router.jobs.new_job(
                        kind=payload.get("kind", ""),
                        prompt=payload.get("prompt", ""),
                        negative=payload.get("negative", ""),
                        params=payload.get("params", {}),
                        input_asset_ids=payload.get("input_asset_ids"),
                        route=payload.get("route", "auto"),
                        requested_provider=payload.get("provider"),
                    )
                    plan = router.plan(job)
                    if plan.get("error"):
                        router.jobs.update(job["id"], state="failed", error="routing: " + plan["error"])
                        self._serve_json({"status": "error", "error": plan["error"]})
                        return
                    est = plan.get("estimate") or {}
                    router.jobs.update(job["id"], provider=plan["provider"], model=plan.get("model"),
                                       cost_estimate_credits=est.get("credits"),
                                       cost_estimate_usd=est.get("usd"),
                                       pricing_table_version=est.get("pricing_table_version"))
                    router.jobs.queue(job)
                    job = router.jobs.get(job["id"])
                    self._serve_json({"status": "ok", "job": job})
                elif path == "/api/media/estimate":
                    fake = {"kind": payload.get("kind", ""), "params": payload.get("params", {}),
                            "requested_provider": payload.get("provider"), "model": payload.get("model")}
                    plan = router.plan(fake)
                    self._serve_json(plan if plan.get("error") is None else {"error": plan["error"]})
                elif path.endswith("/retry") and path.startswith("/api/media/jobs/"):
                    job_id = path[len("/api/media/jobs/"):][:-len("/retry")]
                    job = router.jobs.get(job_id)
                    if job is None:
                        self._serve_json({"status": "error", "error": "unknown job"})
                        return
                    if job.get("state") not in ("failed", "timed_out", "succeeded_provider_download_failed"):
                        self._serve_json({"status": "error", "error": "only failed/timed_out jobs can be retried"})
                        return
                    fields = {"state": "queued", "error": None,
                              "provider_task_id": None, "_poll_count": 0, "_next_poll_at": 0}
                    if job.get("kind") == "character":
                        # user-initiated retry: keep completed pipeline stages,
                        # drop the failed/running tail so it resubmits cleanly
                        # (failed provider generations are auto-refunded upstream).
                        done = [s for s in (job.get("_stages") or []) if s.get("status") == "done"]
                        fields["_stages"] = done
                    router.jobs.update(job_id, **fields)
                    self._serve_json({"status": "ok", "job": router.jobs.get(job_id)})
                else:
                    raise ValueError("unknown media endpoint")
            except ValueError as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            except Exception as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            return

        if path.startswith("/api/openrouter/"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except Exception as e:
                self.send_error(400, f"invalid JSON: {e}")
                return
            try:
                if path == "/api/openrouter/routing":
                    routing = payload.get("routing") or {}
                    if not routing.get("roles"):
                        raise ValueError("routing.roles required")
                    result = {"status": "ok", "applied": _routing_apply(routing)}
                elif path == "/api/openrouter/set-model":
                    model = str(payload.get("model", "")).strip()
                    if not model:
                        raise ValueError("model required")
                    routing = _routing_load()
                    routing.setdefault("roles", {})["primary"] = model
                    result = {"status": "ok", "applied": _routing_apply(routing)}
                elif path == "/api/openrouter/cache-lab":
                    result = {"status": "ok", "lab": _or_cache_lab(
                        payload.get("prompt", ""), payload.get("model", ""))}
                else:
                    raise ValueError("unknown openrouter endpoint")
            except urllib.error.HTTPError as e:
                self._serve_json({"status": "error", "error": f"OpenRouter HTTP {e.code}: {e.reason}"})
                return
            except Exception as e:
                self._serve_json({"status": "error", "error": str(e)})
                return
            self._serve_json(result)
            return

        if path.startswith("/api/team/") and path.endswith("/task"):
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[3] == "task":
                team_name = parts[2]
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                try:
                    payload = json.loads(body)
                    from clawteam.team.tasks import TaskStore
                    store = TaskStore(team_name)
                    task = store.create(
                        subject=payload.get("subject", ""),
                        description=payload.get("description", ""),
                        owner=payload.get("owner", "")
                    )
                    self._serve_json({"status": "ok", "task_id": task.id})
                except Exception as e:
                    self.send_error(400, str(e))
                return
        self.send_error(404)

    _RGDS_TYPES = {
        ".css": "text/css",
        ".js": "text/javascript",
        ".json": "application/json",
        ".md": "text/markdown",
    }

    def _serve_rgds_asset(self, path: str):
        """Serve vendored RGDS assets (static/rgds/) with traversal protection."""
        name = path[len("/rgds/"):]
        if not name or "/" in name or "\\" in name or ".." in name:
            self.send_error(400, "Invalid RGDS asset path")
            return
        filepath = _STATIC_DIR / "rgds" / name
        if not filepath.is_file():
            self.send_error(404, f"RGDS asset not found: {name}")
            return
        suffix = filepath.suffix.lower()
        content_type = self._RGDS_TYPES.get(suffix, "application/octet-stream")
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def _serve_static(self, filename: str, content_type: str):
        filepath = _STATIC_DIR / filename
        if not filepath.exists():
            self.send_error(404, f"Static file not found: {filename}")
            return
        content = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_team(self, team_name: str):
        try:
            data = self.collector.collect_team(team_name)
            self._serve_json(data)
        except ValueError as e:
            body = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _serve_sse(self, team_name: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                try:
                    data = self.team_cache.get(
                        team_name,
                        lambda: self.collector.collect_team(team_name),
                    )
                except ValueError as e:
                    data = {"error": str(e)}
                payload = json.dumps(data, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(self.interval)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format, *args):
        # Suppress default stderr logging for SSE connections
        first = str(args[0]) if args else ""
        if "/api/events/" not in first:
            super().log_message(format, *args)


def serve(
    host: str = "127.0.0.1",
    port: int = 8080,
    default_team: str = "",
    interval: float = 2.0,
):
    """Start the Web UI server."""
    collector = BoardCollector()
    BoardHandler.collector = collector
    BoardHandler.default_team = default_team
    BoardHandler.interval = interval
    BoardHandler.team_cache = TeamSnapshotCache(ttl_seconds=interval)

    from clawteam.media.router import MediaRouter
    BoardHandler.media_router = MediaRouter()
    BoardHandler.media_router.start()

    # Photo lane (operator decision 2026-09-26, option b): uploads live in
    # ~/.clawteam/media/uploads and the loopback photo host is the only thing
    # the public cloudflared hostname may reach. Board up = photo lane up.
    from clawteam.media.uploads import UploadStore, photohost_config
    from clawteam.media.photohost import start_photohost
    BoardHandler.upload_store = UploadStore()
    cfg = photohost_config()
    try:
        start_photohost(port=cfg["port"], uploads=BoardHandler.upload_store)
    except OSError as e:
        print(f"photo host not started (port {cfg['port']}): {e}")

    server = ThreadingHTTPServer((host, port), BoardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
