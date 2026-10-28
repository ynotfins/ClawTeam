"""WP5 — Keep It Simple mode + Parent Gate (KEEP_IT_SIMPLE_SPEC §6/§8/§11).

`~/.clawteam/kis.json` lands inside the pytest sandbox: the autouse
`isolated_data_dir` fixture in tests/conftest.py redirects HOME/USERPROFILE
and CLAWTEAM_DATA_DIR to tmp_path, and `kis_path()` is fixed relative to
`config_path()` (anchor B5). No real PIN material ever exists here.
"""

from __future__ import annotations

import json
import time

import pytest

from clawteam.kis import (
    DEFAULT_CAPS,
    GATED_ACTIONS,
    KisState,
    ParentGateError,
    kis_path,
)


@pytest.fixture(autouse=True)
def clean_kis_file():
    """Ensure a clean slate per test (conftest already sandboxes HOME)."""
    p = kis_path()
    if p.exists():
        p.unlink()
    yield p
    if p.exists():
        p.unlink()


class TestParentGate:
    def test_pin_stored_hashed_never_plaintext(self):
        state = KisState.set_pin("4321")
        raw = kis_path().read_text(encoding="utf-8")
        assert "4321" not in raw                    # never plaintext, never logged
        assert "pin_hash" in raw and "pin_salt" in raw
        assert "pin_hash" not in state             # returned dict carries no hash

    def test_verify_roundtrip(self):
        KisState.set_pin("4321")
        KisState.verify_pin("4321")
        with pytest.raises(ParentGateError, match="wrong PIN"):
            KisState.verify_pin("9999")

    def test_unconfigured_gate_refuses(self):
        with pytest.raises(ParentGateError, match="not configured"):
            KisState.verify_pin("4321")

    def test_five_wrong_pins_lock_out(self):
        KisState.set_pin("4321")
        for _ in range(4):
            with pytest.raises(ParentGateError, match="wrong PIN"):
                KisState.verify_pin("0000")
        with pytest.raises(ParentGateError, match="wrong PIN"):
            KisState.verify_pin("0000")            # 5th wrong arms the lockout
        with pytest.raises(ParentGateError, match="locked out"):
            KisState.verify_pin("4321")            # even the right PIN is locked out
        state = json.loads(kis_path().read_text(encoding="utf-8"))
        assert state["lockout_until"] > time.time()

    def test_gate_actions_cover_spec(self):
        assert "disable_keep_it_simple" in GATED_ACTIONS
        assert "approve_person_photo" in GATED_ACTIONS
        assert "approve_voice_clone" in GATED_ACTIONS
        assert "publish_external" in GATED_ACTIONS

    def test_gate_approves_with_pin_rejects_without(self):
        KisState.set_pin("4321")
        assert KisState.gate("publish_external", "4321")["approved"] is True
        with pytest.raises(ParentGateError, match="unknown gated action"):
            KisState.gate("do_anything", "4321")
        with pytest.raises(ParentGateError):
            KisState.gate("delete_project", "0000")


class TestKisMode:
    def test_default_off_and_on_freely(self):
        assert KisState.enabled() is False
        KisState.set_enabled(True)
        assert KisState.enabled() is True          # ON is free (kids default-safe)

    def test_off_requires_gate(self):
        KisState.set_pin("4321")
        KisState.set_enabled(True)
        with pytest.raises(ParentGateError, match="wrong PIN"):
            KisState.set_enabled(False, pin="0000")
        assert KisState.enabled() is True         # wrong PIN keeps Simple ON
        KisState.set_enabled(False, pin="4321")
        assert KisState.enabled() is False

    def test_off_without_pin_is_free_when_gate_unset(self):
        # No PIN ever set → OFF stays free (first enable defines the gate).
        KisState.set_enabled(True)
        KisState.set_enabled(False)
        assert KisState.enabled() is False


class TestCaps:
    def test_defaults_match_spec(self):
        caps = KisState.caps()
        assert caps["credits_per_run"] == 40
        assert caps["credits_per_day_per_profile"] == 150
        assert caps["movie_preset_total"] == 120
        assert caps["wall_clock_minutes_per_run"] == 45
        assert caps["concurrent_jobs"] == 2
        assert DEFAULT_CAPS["movie_gate_approval_above"] == 60

    def test_cap_changes_require_gate(self):
        KisState.set_pin("4321")
        with pytest.raises(ParentGateError, match="wrong PIN"):
            KisState.set_caps({"credits_per_run": 99}, pin="0000")
        caps = KisState.set_caps({"credits_per_run": 60}, pin="4321")
        assert caps["credits_per_run"] == 60
        assert KisState.caps()["credits_per_day_per_profile"] == 150  # untouched


class TestPolicySnapshot:
    def test_policy_shape_and_no_secret_material(self):
        KisState.set_pin("4321")
        policy = KisState.policy()
        assert policy["gate_configured"] is True
        assert policy["enabled"] is False
        assert policy["locked_out"] is False
        assert "pin_hash" not in json.dumps(policy)     # no PIN material on the wire
        assert set(policy["caps"]) == set(DEFAULT_CAPS)
        assert set(policy["gated_actions"]) == set(GATED_ACTIONS)


class TestBoardRoutes:
    """§11 routes via BoardHandler (same construction pattern as test_board.py)."""

    @staticmethod
    def _make_handler(path: str, body: bytes, command: str = "POST"):
        import io
        from clawteam.board.server import BoardHandler
        handler = object.__new__(BoardHandler)
        handler.path = path
        handler.command = command
        handler.headers = {"Content-Length": str(len(body))} if body else {}
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        # bare-handler stubs (no socket): keep stdlib from touching
        # requestline/client_address in send_response/log_message paths
        handler.log_message = lambda *a, **kw: None
        handler.send_response = lambda *a, **kw: None
        handler.send_header = lambda *a, **kw: None
        handler.end_headers = lambda: None
        served: dict = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        return handler, served

    @classmethod
    def _post(cls, path: str, payload: dict) -> dict:
        handler, served = cls._make_handler(path, json.dumps(payload).encode("utf-8"), "POST")
        handler.do_POST()
        return served["data"]

    @classmethod
    def _get(cls, path: str) -> dict:
        handler, served = cls._make_handler(path, b"", "GET")
        handler.do_GET()
        return served["data"]

    def test_mode_route_roundtrip(self):
        assert self._get("/api/kis/mode") == {"enabled": False}
        out = self._post("/api/kis/mode", {"enabled": True})
        assert out == {"status": "ok", "enabled": True}
        # gate unset: OFF is free (first PIN defines the gate)
        out = self._post("/api/kis/mode", {"enabled": False})
        assert out == {"status": "ok", "enabled": False}
        # gate configured: OFF without PIN → gate_required, stays ON
        self._post("/api/kis/parent-gate/set", {"pin": "4321"})
        self._post("/api/kis/mode", {"enabled": True})
        err = self._post("/api/kis/mode", {"enabled": False})
        assert err["status"] == "error" and err.get("gate_required") is True
        assert KisState.enabled() is True
        ok = self._post("/api/kis/mode", {"enabled": False, "pin": "4321"})
        assert ok == {"status": "ok", "enabled": False}

    def test_parent_gate_routes(self):
        out = self._post("/api/kis/parent-gate/set", {"pin": "4321"})
        assert out == {"status": "ok", "configured": True}
        out = self._post("/api/kis/parent-gate/verify", {"pin": "9999"})
        assert out["status"] == "error" and out["gate_required"] is True
        out = self._post("/api/kis/parent-gate/verify", {"pin": "4321"})
        assert out == {"status": "ok", "verified": True}

    def test_policy_route_clean(self):
        KisState.set_pin("4321")
        policy = self._get("/api/kis/policy")
        assert policy["gate_configured"] is True
        assert "pin_hash" not in json.dumps(policy)