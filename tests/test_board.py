from __future__ import annotations

import io
from pathlib import Path

import pytest

from clawteam.board.collector import BoardCollector
from clawteam.board.server import BoardHandler, _fetch_proxy_content, _normalize_proxy_target
from clawteam.team.mailbox import MailboxManager
from clawteam.team.manager import TeamManager


def test_collect_overview_does_not_call_collect_team(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )

    def fail_collect_team(self, team_name: str):
        raise AssertionError("collect_team should not be called for overview")

    monkeypatch.setattr(BoardCollector, "collect_team", fail_collect_team)

    teams = BoardCollector().collect_overview()

    assert teams == [
        {
            "name": "demo",
            "description": "demo team",
            "leader": "leader",
            "members": 1,
            "tasks": 0,
            "pendingMessages": 0,
        }
    ]


def test_collect_overview_sums_inbox_counts_for_all_members(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001")
    MailboxManager("demo").send(from_agent="leader", to="worker", content="hello")

    def fail_collect_team(self, team_name: str):
        raise AssertionError("collect_team should not be called for overview")

    monkeypatch.setattr(BoardCollector, "collect_team", fail_collect_team)

    teams = BoardCollector().collect_overview()

    assert teams == [
        {
            "name": "demo",
            "description": "demo team",
            "leader": "leader",
            "members": 2,
            "tasks": 0,
            "pendingMessages": 1,
        }
    ]


def test_team_snapshot_cache_reuses_value_within_ttl():
    from clawteam.board.server import TeamSnapshotCache

    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"version": calls["count"]}

    cache = TeamSnapshotCache(ttl_seconds=60.0)

    first = cache.get("demo", loader)
    second = cache.get("demo", loader)

    assert first == {"version": 1}
    assert second == {"version": 1}
    assert calls["count"] == 1


def test_team_snapshot_cache_expires_after_ttl(monkeypatch):
    from clawteam.board.server import TeamSnapshotCache

    now = {"value": 100.0}
    monkeypatch.setattr("clawteam.board.server.time.monotonic", lambda: now["value"])

    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"version": calls["count"]}

    cache = TeamSnapshotCache(ttl_seconds=5.0)

    first = cache.get("demo", loader)
    now["value"] += 10.0
    second = cache.get("demo", loader)

    assert first == {"version": 1}
    assert second == {"version": 2}
    assert calls["count"] == 2


def test_collect_team_preserves_conflicts_field(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )

    data = BoardCollector().collect_team("demo")

    assert "conflicts" in data


def test_collect_team_exposes_member_inbox_identity(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001", user="alice")

    data = BoardCollector().collect_team("demo")

    worker = next(member for member in data["members"] if member["name"] == "worker")
    assert worker["memberKey"] == "alice_worker"
    assert worker["inboxName"] == "alice_worker"


def test_collect_team_normalizes_message_participants(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        description="demo team",
    )
    TeamManager.add_member("demo", "worker", "worker001", user="alice")
    mailbox = MailboxManager("demo")
    mailbox.send(from_agent="leader", to="worker", content="hello")
    mailbox.broadcast(from_agent="leader", content="broadcast")

    data = BoardCollector().collect_team("demo")

    direct = next(msg for msg in data["messages"] if msg.get("content") == "hello")
    assert direct["fromKey"] == "leader"
    assert direct["fromLabel"] == "leader"
    assert direct["toKey"] == "alice_worker"
    assert direct["toLabel"] == "worker"
    assert direct["isBroadcast"] is False

    broadcast = next(
        msg
        for msg in data["messages"]
        if msg.get("content") == "broadcast" and msg.get("to") == "alice_worker"
    )
    assert broadcast["fromKey"] == "leader"
    assert broadcast["toKey"] == "alice_worker"
    assert broadcast["toLabel"] == "worker"
    assert broadcast["isBroadcast"] is True


def test_collect_overview_preserves_broken_team_fallback(monkeypatch):
    def fake_discover():
        return [
            {
                "name": "good",
                "description": "good team",
                "memberCount": 1,
            },
            {
                "name": "broken",
                "description": "broken team",
                "memberCount": 7,
            },
        ]

    def fake_summary(self, team_name: str):
        if team_name == "broken":
            raise ValueError("boom")
        return {
            "name": "good",
            "description": "good team",
            "leader": "lead",
            "members": 1,
            "tasks": 3,
            "pendingMessages": 2,
        }

    monkeypatch.setattr(TeamManager, "discover_teams", staticmethod(fake_discover))
    monkeypatch.setattr(BoardCollector, "collect_team_summary", fake_summary)

    overview = BoardCollector().collect_overview()

    assert overview == [
        {
            "name": "good",
            "description": "good team",
            "leader": "lead",
            "members": 1,
            "tasks": 3,
            "pendingMessages": 2,
        },
        {
            "name": "broken",
            "description": "broken team",
            "leader": "",
            "members": 7,
            "tasks": 0,
            "pendingMessages": 0,
        },
    ]


def test_serve_team_reads_fresh_snapshot_without_cache(monkeypatch):
    calls = {"count": 0}
    served = {}

    class FakeCache:
        def get(self, team_name, loader):
            raise AssertionError("team cache should not be used for /api/team")

    handler = object.__new__(BoardHandler)
    handler.collector = type(
        "Collector",
        (),
        {
            "collect_team": staticmethod(
                lambda team_name: calls.__setitem__("count", calls["count"] + 1)
                or {"team": {"name": team_name}}
            )
        },
    )()
    handler.team_cache = FakeCache()
    handler._serve_json = lambda data: served.setdefault("data", data)

    handler._serve_team("demo")

    assert calls["count"] == 1
    assert served["data"] == {"team": {"name": "demo"}}


def test_serve_sse_uses_shared_team_snapshot_cache(monkeypatch):
    calls = {"count": 0}

    class FakeCache:
        def get(self, team_name, loader):
            calls["count"] += 1
            return loader()

    handler = object.__new__(BoardHandler)
    handler.collector = type(
        "Collector",
        (),
        {"collect_team": staticmethod(lambda team_name: {"team": {"name": team_name}})},
    )()
    handler.team_cache = FakeCache()
    handler.interval = 0.0
    handler.wfile = io.BytesIO()
    handler.send_response = lambda code: None
    handler.send_header = lambda name, value: None
    handler.end_headers = lambda: None
    monkeypatch.setattr(
        handler.wfile,
        "flush",
        lambda: (_ for _ in ()).throw(BrokenPipeError()),
    )

    handler._serve_sse("demo")

    assert calls["count"] == 1


def test_proxy_rejects_non_github_targets():
    with pytest.raises(ValueError, match="GitHub-hosted"):
        _normalize_proxy_target("https://example.com/secret")


def test_proxy_rejects_localhost_targets():
    with pytest.raises(ValueError, match="not allowed"):
        _normalize_proxy_target("https://127.0.0.1/admin")


def test_proxy_rejects_non_https_targets():
    with pytest.raises(ValueError, match="https"):
        _normalize_proxy_target("http://raw.githubusercontent.com/org/repo/main/README.md")


def test_proxy_rejects_metadata_targets():
    with pytest.raises(ValueError, match="not allowed"):
        _normalize_proxy_target("https://169.254.169.254/latest/meta-data")


def test_proxy_rejects_redirect_to_disallowed_host(monkeypatch):
    class FakeResponse:
        def __init__(self, url: str, payload: bytes):
            self._url = url
            self._payload = payload

        def geturl(self):
            return self._url

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeOpener:
        def open(self, req, timeout=10):
            return FakeResponse("https://example.com/payload", b"redirected")

    monkeypatch.setattr("clawteam.board.server.urllib.request.build_opener", lambda *_: FakeOpener())

    with pytest.raises(ValueError, match="GitHub-hosted"):
        _fetch_proxy_content("https://raw.githubusercontent.com/org/repo/main/README.md")


def test_proxy_fetches_allowed_github_content(monkeypatch):
    seen = {}

    class FakeResponse:
        def __init__(self, url: str, payload: bytes):
            self._url = url
            self._payload = payload

        def geturl(self):
            return self._url

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeOpener:
        def open(self, req, timeout=10):
            seen["url"] = req.full_url
            return FakeResponse(req.full_url, b"ok")

    monkeypatch.setattr("clawteam.board.server.urllib.request.build_opener", lambda *_: FakeOpener())

    assert _fetch_proxy_content("https://raw.githubusercontent.com/org/repo/main/README.md") == b"ok"
    assert seen["url"] == "https://raw.githubusercontent.com/org/repo/main/README.md"


def test_board_ui_escapes_attacker_controlled_fields():
    html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")

    assert "escapeHtml(m.name)" in html
    assert "escapeHtml(m.agentType || 'Agent')" in html
    assert "escapeHtml(m.fromLabel || m.from || 'SYS')" in html
    assert "escapeHtml(m.toLabel || m.to || 'ALL')" in html
    assert "escapeHtml(t.owner || 'Unassigned')" in html
    assert "t.blockedBy.map(v => escapeHtml(v)).join(', ')" in html
    assert "option.textContent =" in html
    assert "document.getElementById('ui-meta').innerText =" in html
    assert "`${t.name || ''}${t.description ? ` - ${t.description}` : ''}`" in html


def test_rgds_assets_are_vendored_and_linked():
    """RGDS (@r3lentless/rgds-web) is the board's design system: the published
    dist assets must be vendored, provenance-locked, and linked before the
    board stylesheet."""
    import json

    rgds_dir = Path("clawteam/board/static/rgds")
    for asset in ("tokens.css", "interaction.css", "components.css",
                  "animations.css", "form-factor.css", "package.json", "PROVENANCE.md"):
        assert (rgds_dir / asset).is_file(), f"missing vendored RGDS asset: {asset}"

    pkg = json.loads((rgds_dir / "package.json").read_text(encoding="utf-8"))
    theme = json.loads(Path("design/theme.tokens.json").read_text(encoding="utf-8"))
    provenance = (rgds_dir / "PROVENANCE.md").read_text(encoding="utf-8")
    assert pkg["name"] == "@r3lentless/rgds-web"
    # Version invariant: package, domain layer, and provenance must agree.
    assert pkg["version"] == theme["rgds"]["version"]
    assert pkg["version"] in provenance
    assert theme["rgds"]["figma_file_key"] == "KbhSAUCrADaqhxOm7jM2FC"

    html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")
    first_style = html.index("<style>")
    for link in ("/rgds/tokens.css", "/rgds/interaction.css",
                 "/rgds/components.css", "/rgds/animations.css", "/rgds/form-factor.css"):
        assert link in html[:first_style], f"{link} must be linked before the board <style>"

    tokens_css = (rgds_dir / "tokens.css").read_text(encoding="utf-8")
    for mode in ("primary-light", "secondary-light", "primary-dark", "secondary-dark"):
        assert f':root[data-theme="{mode}"]' in tokens_css, f"RGDS mode missing: {mode}"


def test_board_ui_has_no_color_literals():
    """Zero-hardcoding law: the board UI carries no color literals at all.
    The only permitted oklch()/hex literals are RGDS's own published scrim
    fallback, mirrored verbatim from rgds components.css inside var() defaults."""
    import re

    html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", html), "hex color literal in board UI"
    assert not re.search(r"\brgba?\(", html), "rgb()/rgba() literal in board UI"
    oklch_sites = [m.start() for m in re.finditer(r"oklch\(", html)]
    scrim_fallback = "var(--md-sys-color-scrim, oklch(0% 0 0 / 0.48))"
    expected_prefix = scrim_fallback[:scrim_fallback.index("oklch(")]
    for site in oklch_sites:
        assert html[html.rfind("var(", 0, site):site] == expected_prefix, (
            "oklch literal outside the RGDS scrim var() fallback")


def test_board_ui_rainbow_is_stroke_only():
    """Dynamic stroke law: any background using var(--stroke-gradient) as a
    border-box layer must sit under an opaque padding-box fill — a translucent
    fill lets the rainbow bleed into the box interior (forbidden fill)."""
    import re

    html = Path("clawteam/board/static/index.html").read_text(encoding="utf-8")
    decls = re.findall(r"background:\s*[^;{}]+;", html)
    offenders = [d for d in decls if "var(--stroke-gradient)" in d and "transparent" in d]
    assert not offenders, (
        "rainbow bleed: stroke-gradient backgrounds with translucent fills: "
        + " || ".join(offenders))


def test_theme_tokens_json_is_rgds_domain_layer():
    """design/theme.tokens.json must be the RGDS domain layer: RGDS mode ids,
    var() references only, and no color values or NFA overlay remnants."""
    import json
    import re

    theme = json.loads(Path("design/theme.tokens.json").read_text(encoding="utf-8"))
    assert theme["$schema"] == "clawteam-board-theme/2"
    assert set(theme["modes"]) == {"primary-light", "secondary-light",
                                   "primary-dark", "secondary-dark"}
    assert theme["rgds"]["package"] == "@r3lentless/rgds-web"
    assert "nfa" not in json.dumps(theme), "NFA overlay must not survive in the domain layer"
    for mode in theme["modes"].values():
        for token, value in mode.get("tokens", {}).items():
            assert isinstance(value, str) and value.startswith("var(--"), (
                f"domain token {token} must be a var() reference, got {value!r}")
    assert set(theme["legacyModeMap"]) == {"light-google", "light-orange",
                                           "dark-speakeasy", "dark-orange"}
