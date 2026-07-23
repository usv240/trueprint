"""Central configuration — loads secrets from the project-root .env."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# project root = two levels up from this file (backend/app/config.py -> root)
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _get(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v.strip() if isinstance(v, str) else v


class Config:
    # --- Backblaze B2 (S3-compatible) ---
    B2_KEY_ID = _get("B2_KEY_ID")
    B2_APP_KEY = _get("B2_APP_KEY")
    B2_BUCKET = _get("B2_BUCKET", "trueprint")
    B2_S3_ENDPOINT = _get("B2_S3_ENDPOINT")           # e.g. s3.us-east-005.backblazeb2.com
    B2_REGION = _get("B2_REGION")                     # e.g. us-east-005
    B2_BUCKET_ID = _get("B2_BUCKET_ID")

    @property
    def b2_endpoint_url(self) -> str:
        ep = self.B2_S3_ENDPOINT or ""
        return ep if ep.startswith("http") else f"https://{ep}"

    # --- GMI Cloud ---
    # IMPORTANT: chat (OpenAI-compatible) and image (request-queue) use DIFFERENT base URLs.
    GMI_API_KEY = _get("GMI_API_KEY")
    GMI_CHAT_BASE_URL = _get("GMI_CHAT_BASE_URL", "https://api.gmi-serving.com/v1")
    GMI_IMAGE_BASE_URL = _get("GMI_IMAGE_BASE_URL",
                              "https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey")
    GMI_MODEL_VISION = _get("GMI_MODEL_VISION", "google/gemini-3.6-flash")
    GMI_MODEL_RESTORE = _get("GMI_MODEL_RESTORE", "bria-fibo-restore")
    GMI_MODEL_RECOLOR = _get("GMI_MODEL_RECOLOR", "gpt-image-2-edit")
    GMI_MODEL_EDIT = _get("GMI_MODEL_EDIT", "gpt-image-2-edit")
    GMI_MODEL_INPAINT = _get("GMI_MODEL_INPAINT", "bria-genfill")
    GMI_MODEL_ERASE = _get("GMI_MODEL_ERASE", "bria-eraser")
    GMI_MODEL_COLORIZE_ALT = _get("GMI_MODEL_COLORIZE_ALT", "gpt-image-2-edit")
    GMI_MODEL_COLORIZE_ALT2 = _get("GMI_MODEL_COLORIZE_ALT2", "hunyuan-image-to-image")
    GMI_MODEL_UPSCALE = _get("GMI_MODEL_UPSCALE")
    GMI_MODEL_AUDIO = _get("GMI_MODEL_AUDIO")

    def require_b2(self) -> None:
        missing = [k for k in ("B2_KEY_ID", "B2_APP_KEY", "B2_S3_ENDPOINT", "B2_REGION")
                   if not getattr(self, k)]
        if missing:
            raise RuntimeError(f"Missing B2 config in .env: {', '.join(missing)}")

    def require_gmi(self) -> None:
        if not self.GMI_API_KEY:
            raise RuntimeError("Missing GMI_API_KEY in .env")


config = Config()
