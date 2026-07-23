"""Custom Genblaze providers for Trueprint.

Genblaze's generic image provider maps payloads via the model registry. For
models not in the bundled registry (e.g. gpt-image-2-edit), the generic mapping
produces a body GMICloud rejects. We subclass and emit the exact payload each
model expects, while keeping all of Genblaze's Pipeline / manifest / lineage /
retry machinery.
"""
from __future__ import annotations
from typing import Any
from genblaze_gmicloud import GMICloudImageProvider
from genblaze_core.models.step import Step

# Per-model required payload shape (reverse-engineered from the request queue).
#   image  -> the input image URL
#   prompt -> instruction
_IMAGE_URL_KEY = {
    "gpt-image-2-edit": "image",
    "hunyuan-image-to-image": "image",
    "bria-fibo-restore": "image",
    "seededit-3-0-i2i-250628": "image",
}


def _first_input_url(step: Step) -> str | None:
    for attr in ("inputs", "assets"):
        for a in (getattr(step, attr, None) or []):
            u = getattr(a, "url", None)
            if u:
                return u
    return None


class TrueprintImageProvider(GMICloudImageProvider):
    """GMICloud image provider that emits model-correct request-queue payloads."""

    def prepare_payload(self, step: Step, *, base_params: dict[str, Any] | None = None,
                        validate_inputs: bool = True) -> dict[str, Any]:
        # SSRF-validate chained inputs, mirroring the base implementation.
        if validate_inputs:
            try:
                from genblaze import validate_chain_input_url
                for a in (getattr(step, "inputs", None) or []):
                    if getattr(a, "url", None):
                        validate_chain_input_url(a.url)
            except Exception:
                pass

        payload: dict[str, Any] = {}
        if step.prompt:
            payload["prompt"] = step.prompt

        url = _first_input_url(step)
        if url:
            key = _IMAGE_URL_KEY.get(step.model, "image")
            payload[key] = url

        # explicit per-step params win (e.g. size, seed, guidance)
        for k, v in (getattr(step, "params", None) or {}).items():
            payload[k] = v
        return payload
