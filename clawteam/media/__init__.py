"""Multimedia Suite: app-owned media generation boundary.

Providers (local ComfyUI, KIE.ai cloud) sit behind this package; the board UI
only ever sees normalized job/asset shapes and lifecycle states.
"""

from clawteam.media.jobs import MediaJobStore, JOB_STATES, TERMINAL_STATES
from clawteam.media.assets import AssetStore
from clawteam.media.router import MediaRouter

__all__ = ["MediaJobStore", "AssetStore", "MediaRouter", "JOB_STATES", "TERMINAL_STATES"]
