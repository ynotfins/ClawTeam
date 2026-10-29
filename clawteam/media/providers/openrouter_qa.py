"""Forensic visual QA via OpenRouter vision models (D-017 stage 4).

Compares the generated 3D character's preview render against the user's
source photo and returns a strict-JSON verdict the pipeline acts on
(pass / auto-heal). Key from User-scope env OPENROUTER_API_KEY (name only).

Chat-completions contract verified live on this machine 2026-10-27:
POST https://openrouter.ai/api/v1/chat/completions
Authorization: Bearer <OPENROUTER_API_KEY>
messages[].content parts: {"type":"text"|"image_url","image_url":{"url":...}}

QA model: google/gemini-2.5-pro (operator doc, docs/3D-CHARACTER-AND
MOVIE-PRODUCTION.md Layer 1 — best-in-class multimodal window).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

API = "https://openrouter.ai/api/v1/chat/completions"
QA_MODEL = "google/gemini-2.5-pro"

FORENSIC_PROMPT = (
    "You are a forensic 3D-asset QA inspector. IMAGE 1 is the user's source "
    "photo of a person or pet. IMAGE 2 is a preview render of the 3D character "
    "we generated from it. Compare them and answer STRICTLY as JSON with "
    "exactly these fields: \"pass\" (boolean), \"issues\" (array of strings, "
    "empty when pass), \"severity\" (\"none\"|\"low\"|\"medium\"|\"high\"). "
    "Check: identity match (head shape, hair, face structure, clothing), "
    "limb integrity (no merged or missing limbs), and obvious texture or "
    "geometry artifacts. Do not include any text outside the JSON."
)


class QaError(Exception):
    """QA call failed or returned an unparseable verdict."""


def _key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def qa_available() -> bool:
    return bool(_key())


def vision_qa(source_url: str, preview_url: str, *,
              model: str = QA_MODEL, prompt: str = FORENSIC_PROMPT,
              timeout: int = 120) -> dict:
    """Run the forensic comparison. Returns {"pass": bool, "issues": [...],
    "severity": str, "raw": str}. Raises QaError on transport/parse failure."""
    key = _key()
    if not key:
        raise QaError("dormant: OPENROUTER_API_KEY not set (User env)")
    if not source_url or not preview_url:
        raise QaError("vision QA needs both the source photo and the preview render")

    payload = {
        "model": model,
        "max_tokens": 400,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": source_url}},
                {"type": "image_url", "image_url": {"url": preview_url}},
            ],
        }],
    }
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        raise QaError(f"OpenRouter HTTP {e.code}: {body}") from None
    except urllib.error.URLError as e:
        raise QaError(f"OpenRouter unreachable: {e}") from None

    try:
        raw = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    except Exception:
        raw = ""
    if not raw:
        raise QaError("OpenRouter returned no content")

    # Model may wrap JSON in fences — tolerate, never guess beyond one block.
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise QaError(f"unparseable QA verdict: {raw[:200]}")
    try:
        verdict = json.loads(m.group(0))
    except ValueError as e:
        raise QaError(f"invalid QA JSON: {raw[:200]}") from e

    return {
        "pass": bool(verdict.get("pass")),
        "issues": [str(i) for i in (verdict.get("issues") or [])][:10],
        "severity": str(verdict.get("severity", "none")),
        "raw": raw[:1000],
    }