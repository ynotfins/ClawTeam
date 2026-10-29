"""One-click media presets — the "Easy Studio" tile catalog (D-016).

Operator law (D-016, 2026-10-28): the image/video center is for
non-technical family — every popular process is a **premade one-click
tile, Topaz-style**: pick a tile, drop your file or type your idea, press
the button. No knobs unless the user asks for them.

Validation is E6-enforced at load time: every preset's model+kind must be
covered by a verified adapter in `clawteam.media.providers.kie.ADAPTERS`,
so a schema drift or a typo can never reach the family UI.

Preset shape (MEDIA_PRESETS_CATALOG.md lineage):
  {id, title, blurb, example, kind, model, needs, defaults, est_credits, one_click}
  needs: "text" (prompt box) | "image" (photo drop) | "video" (clip drop)
         | "image+text" | "none"
"""

from __future__ import annotations

from clawteam.media.providers import kie


class PresetError(Exception):
    """A preset definition drifted from a verified adapter (E6)."""


# Builtin one-click catalog. Reading level ~ grade 5 (KIS spec §10);
# estimates are the KIE catalog prices, still `verified: false` until a
# live task reports creditsConsumed (E6).
BUILTIN_PRESETS: list[dict] = [
    {
        "id": "sharper-photo",
        "title": "Make My Photo Sharper & Bigger",
        "blurb": "Topaz-quality upscale — clears up blurry or small photos.",
        "kind": "upscale",
        "model": "topaz/image-upscale",
        "needs": "image",
        "defaults": {"upscale_factor": "2"},
        "est_credits": 10.0,
        "one_click": True,
        "example": "A crisp, bigger version of the same photo - sharp enough to print.",
    },
    {
        "id": "sharper-video",
        "title": "Make My Video Sharper",
        "blurb": "Topaz-quality video upscale — crisp, clear, bigger.",
        "kind": "vupscale",
        "model": "topaz/video-upscale",
        "needs": "video",
        "defaults": {"upscale_factor": "2"},
        "est_credits": 48.0,   # ~8cr/s x 6s clip; per-second billing shown before submit
        "one_click": True,
        "example": "The same video, but clear and sharp on a big TV.",
    },
    {
        "id": "make-picture",
        "title": "Make a Picture",
        "blurb": "Type what you want to see. We make it.",
        "kind": "t2img",
        "model": "flux1-kontext",
        "needs": "text",
        "defaults": {"aspect_ratio": "1:1", "output_format": "png"},
        "est_credits": 5.0,
        "one_click": True,
        "example": "A brand-new picture of whatever you typed - like magic.",
    },
    {
        "id": "change-photo",
        "title": "Change My Photo",
        "blurb": "Type what to change — keep everything else the same.",
        "kind": "edit",
        "model": "flux1-kontext",
        "needs": "image+text",
        "defaults": {},
        "est_credits": 5.0,
        "one_click": True,
        "example": "Your same photo with only the change you asked for.",
    },
    {
        "id": "make-video",
        "title": "Make a Video",
        "blurb": "Type your idea. We make a short video with sound.",
        "kind": "t2v",
        "model": "minimax-h3/text-to-video",
        "needs": "text",
        "defaults": {"aspect_ratio": "16:9", "duration": 6, "resolution": "2K"},
        "est_credits": 78.0,   # 13cr/s x 6s at 2K
        "one_click": True,
        "example": "A short video with sound, of exactly what you typed.",
    },
    {
        "id": "photo-to-video",
        "title": "Make My Photo Move",
        "blurb": "Add your photo. Type what should happen. It becomes a video.",
        "kind": "i2v",
        "model": "minimax-h3/image-to-video",
        "needs": "image+text",
        "defaults": {"duration": 6, "resolution": "2K"},
        "est_credits": 78.0,
        "one_click": True,
        "example": "Your photo comes alive as a short video that moves and sounds real.",
    },
]


def validate_presets(presets: list[dict] | None = None) -> list[dict]:
    """E6 gate: every preset must map to a verified adapter kind.

    Raises PresetError naming the offender; returns the validated list.
    """
    presets = presets if presets is not None else BUILTIN_PRESETS
    seen_ids: set[str] = set()
    for p in presets:
        pid = p.get("id", "<no id>")
        if pid in seen_ids:
            raise PresetError(f"preset id '{pid}' is duplicated")
        seen_ids.add(pid)
        adapter = kie.ADAPTERS.get(p.get("model", ""))
        if adapter is None:
            raise PresetError(
                f"preset '{pid}' names model '{p.get('model')}' — no verified KIE "
                "adapter (E6: verify the schema on docs.kie.ai before adding)"
            )
        if p.get("kind") not in adapter.kinds:
            raise PresetError(
                f"preset '{pid}': model '{p['model']}' does not support kind "
                f"'{p.get('kind')}' (adapter kinds: {adapter.kinds})"
            )
        if p.get("needs") not in ("text", "image", "video", "image+text", "none"):
            raise PresetError(f"preset '{pid}': unknown needs '{p.get('needs')}'")
        if not p.get("title") or not p.get("blurb"):
            raise PresetError(f"preset '{pid}': family UI needs a title and blurb")
        if not p.get("example"):
            raise PresetError(f"preset '{pid}': family UI needs an example (D-018)")
    return presets


def load_presets() -> list[dict]:
    """The validated one-click catalog (builtins today; user files later)."""
    return validate_presets()


def preset_job_spec(preset: dict, prompt: str = "", source_url: str = "") -> dict:
    """Turn a tile click into a ready-to-create media job spec."""
    params = dict(preset.get("defaults") or {})
    if source_url:
        params["source_url"] = source_url
    return {
        "kind": preset["kind"],
        "model": preset["model"],
        "prompt": prompt or preset.get("blurb", ""),
        "params": params,
        "requested_provider": "kie",
        "preset_id": preset["id"],
        "est_credits": preset.get("est_credits"),
    }