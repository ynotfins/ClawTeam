"""Provider boundary: every execution engine implements this interface.

Normalized shapes only — provider payloads never cross this line.
"""

from __future__ import annotations

from typing import Protocol


class ProviderResult:
    """Normalized provider status snapshot returned by poll()."""

    def __init__(self, *, state: str, provider_status: str | None = None,
                 output_urls: list[str] | None = None, error: str | None = None,
                 actual_credits: float | None = None, actual_usd: float | None = None):
        self.state = state            # running | succeeded | failed
        self.provider_status = provider_status
        self.output_urls = output_urls or []
        self.error = error
        self.actual_credits = actual_credits
        self.actual_usd = actual_usd


class MediaProvider(Protocol):
    name: str

    def capabilities(self) -> dict:
        """{kinds: [..], models: [..], limits: {...}} for routing + UI."""

    def health(self) -> dict:
        """{ok: bool, detail, gates: {name: ok}} — local gates / cloud key presence."""

    def estimate(self, kind: str, model: str, params: dict) -> dict:
        """{credits, usd, pricing_table_version, verified: bool}."""

    def submit(self, job: dict, input_asset_paths: list[str]) -> str:
        """Submit and return the provider task id."""

    def poll(self, task_id: str, kind: str) -> ProviderResult:
        """One poll tick; never sleeps."""

    def download(self, url: str) -> tuple[bytes, str]:
        """Fetch output bytes + extension before the link expires."""
