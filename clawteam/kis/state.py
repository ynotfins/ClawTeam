"""Keep It Simple mode + Parent Gate (docs/KEEP_IT_SIMPLE_SPEC.md §6/§8/§11).

State lives at `~/.clawteam/kis.json` — a FIXED root (anchor B5), separate
from `CLAWTEAM_DATA_DIR`, exactly like `config.json`:
`{enabled, caps, pin_hash, pin_salt, lockout_until, failed_attempts}`.

The PIN is stored as a **scrypt salted hash** (stdlib `hashlib.scrypt`) —
never plaintext, never logged. The gate protects: turning KIS **off**,
cap changes, external publishes, photo-of-a-person and voice-clone
approvals, credit-cap raises, project deletion (§6). Five wrong PINs →
5-minute lockout. Parent Gate approvals are guardian consents, **not**
agent questions — F5 holds.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from clawteam.config import config_path

LOCKOUT_SECONDS = 5 * 60          # §6: 5 wrong PINs → 5-minute lockout
MAX_FAILED_ATTEMPTS = 5

# §8 defaults (guardian-editable behind the Gate)
DEFAULT_CAPS: dict[str, float] = {
    "credits_per_run": 40,
    "credits_per_day_per_profile": 150,
    "movie_preset_total": 120,
    "movie_gate_approval_above": 60,
    "wall_clock_minutes_per_run": 45,
    "concurrent_jobs": 2,
}

# §6: actions that require the Parent Gate
GATED_ACTIONS = (
    "disable_keep_it_simple",
    "change_caps",
    "publish_external",
    "approve_person_photo",
    "approve_voice_clone",
    "raise_credit_cap",
    "delete_project",
)


def kis_path() -> Path:
    """Fixed location `~/.clawteam/kis.json` (anchor B5; never CLAWTEAM_DATA_DIR)."""
    return config_path().parent / "kis.json"


def _load() -> dict:
    p = kis_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save(state: dict) -> None:
    p = kis_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(p))


def _hash_pin(pin: str, salt: bytes) -> str:
    return hashlib.scrypt(pin.encode("utf-8"), salt=salt,
                          n=2 ** 15, r=8, p=1, maxmem=64 * 1024 * 1024).hex()


class ParentGateError(Exception):
    """Gate refused: wrong PIN, not set, or locked out."""


class KisState:
    """One shared Keep-It-Simple state (`~/.clawteam/kis.json`)."""

    # ------------------------------------------------------------------
    # Mode
    # ------------------------------------------------------------------

    @staticmethod
    def enabled() -> bool:
        return bool(_load().get("enabled", False))

    @staticmethod
    def set_enabled(value: bool, pin: str | None = None) -> dict:
        """Turn KIS on freely; turning it OFF needs the Parent Gate (§6)."""
        state = _load()
        if value is False and state.get("pin_hash"):
            KisState.verify_pin(pin or "")        # raises ParentGateError
        state["enabled"] = bool(value)
        _save(state)
        return state

    # ------------------------------------------------------------------
    # Parent Gate (§6)
    # ------------------------------------------------------------------

    @staticmethod
    def set_pin(pin: str) -> dict:
        """Guardian sets the PIN on first enable (salted scrypt hash)."""
        pin = (pin or "").strip()
        if len(pin) < 4:
            raise ParentGateError("PIN must be at least 4 characters")
        state = _load()
        salt = secrets.token_bytes(16)
        state["pin_hash"] = _hash_pin(pin, salt)
        state["pin_salt"] = salt.hex()
        state["failed_attempts"] = 0
        state["lockout_until"] = 0
        _save(state)
        return {k: v for k, v in state.items() if k not in ("pin_hash", "pin_salt")}

    @staticmethod
    def gate_configured() -> bool:
        return bool(_load().get("pin_hash"))

    @staticmethod
    def _lockout_remaining(state: dict) -> int:
        until = int(state.get("lockout_until", 0) or 0)
        return max(0, until - int(time.time()))

    @staticmethod
    def verify_pin(pin: str) -> dict:
        """Verify the PIN. Raises ParentGateError on wrong/locked/not-set."""
        state = _load()
        if not state.get("pin_hash"):
            raise ParentGateError("Parent Gate not configured — guardian must set a PIN first")
        remaining = KisState._lockout_remaining(state)
        if remaining > 0:
            raise ParentGateError(f"locked out — try again in {remaining // 60 + 1} min")
        salt = bytes.fromhex(state.get("pin_salt", "") or "00" * 16)
        if not hmac.compare_digest(_hash_pin(pin or "", salt), state.get("pin_hash", "")):
            failed = int(state.get("failed_attempts", 0)) + 1
            state["failed_attempts"] = failed
            if failed >= MAX_FAILED_ATTEMPTS:
                state["lockout_until"] = int(time.time()) + LOCKOUT_SECONDS
                state["failed_attempts"] = 0
            _save(state)
            raise ParentGateError("wrong PIN")
        state["failed_attempts"] = 0
        _save(state)
        return {k: v for k, v in state.items() if k not in ("pin_hash", "pin_salt")}

    @staticmethod
    def gate(action: str, pin: str) -> dict:
        """Approve one gated action (§6). Approvals are guardian consents —
        they never become agent questions (F5 holds)."""
        if action not in GATED_ACTIONS:
            raise ParentGateError(f"unknown gated action '{action}'")
        KisState.verify_pin(pin)
        return {"action": action, "approved": True}

    # ------------------------------------------------------------------
    # Caps (§8)
    # ------------------------------------------------------------------

    @staticmethod
    def caps() -> dict:
        state = _load()
        caps = dict(DEFAULT_CAPS)
        saved = state.get("caps")
        if isinstance(saved, dict):
            caps.update({k: v for k, v in saved.items() if k in caps})
        return caps

    @staticmethod
    def set_caps(updates: dict, pin: str | None = None) -> dict:
        """Cap changes sit behind the Gate (§6: change_caps)."""
        KisState.verify_pin(pin or "")
        state = _load()
        caps = dict(DEFAULT_CAPS)
        caps.update(state.get("caps") or {})
        caps.update({k: float(v) for k, v in updates.items() if k in caps})
        state["caps"] = caps
        _save(state)
        return caps

    # ------------------------------------------------------------------
    # Board-facing snapshot (§11 /api/kis/policy)
    # ------------------------------------------------------------------

    @staticmethod
    def policy() -> dict:
        state = _load()
        return {
            "enabled": bool(state.get("enabled", False)),
            "gate_configured": bool(state.get("pin_hash")),
            "locked_out": KisState._lockout_remaining(state) > 0,
            "caps": KisState.caps(),
            "gated_actions": list(GATED_ACTIONS),
        }