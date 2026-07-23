"""Submit minimal REAL payloads to several models to see which actually accept a job."""
from __future__ import annotations
import sys, io, json
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config
QUEUE = config.GMI_IMAGE_BASE_URL


def presign() -> str:
    from genblaze_s3 import S3StorageBackend
    from PIL import Image, ImageDraw
    img = Image.new("L", (512, 512), 205); d = ImageDraw.Draw(img)
    d.ellipse((170, 120, 342, 330), fill=150); d.line((0, 70, 512, 480), fill=25, width=4)
    buf = io.BytesIO(); img.convert("RGB").save(buf, "PNG")
    be = S3StorageBackend.for_backblaze(config.B2_BUCKET, region=config.B2_REGION,
                                        key_id=config.B2_KEY_ID, app_key=config.B2_APP_KEY, preflight=True)
    be.put("trueprint/_healthcheck/probe.png", buf.getvalue(), content_type="image/png")
    u = be.presigned_get_url("trueprint/_healthcheck/probe.png", expires_in=3600)
    return u if isinstance(u, str) else getattr(u, "url", str(u))


def main():
    url = presign()
    P = "a red apple on a wooden table, natural light"
    cases = [
        ("seedream-5.0-lite", {"prompt": P}),
        ("seedream-5.0-pro", {"prompt": P}),
        ("gpt-image-2-generate", {"prompt": P}),
        ("reve-2-1", {"prompt": P}),
        ("wan2.7-image", {"text": P}),
        ("bria-fibo-restore", {"image": url}),
        ("hunyuan-image-to-image", {"image": url, "prompt": P}),
        ("gpt-image-2-edit", {"prompt": "colorize this", "image": url}),
        ("seededit-3-0-i2i-250628", {"prompt": "colorize this", "image": url}),
    ]
    h = {"Authorization": f"Bearer {config.GMI_API_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60) as c:
        for model, payload in cases:
            try:
                r = c.post(f"{QUEUE}/requests", headers=h, json={"model": model, "payload": payload})
                body = r.text[:150].replace("\n", " ")
                rid = ""
                if r.status_code < 300:
                    try:
                        j = r.json(); rid = j.get("request_id") or j.get("id") or ""
                    except Exception:
                        pass
                verdict = "ACCEPTED job=" + str(rid) if r.status_code < 300 else f"HTTP {r.status_code}"
                print(f"{model:28s} {verdict:22s} {body if r.status_code>=300 else ''}")
            except Exception as e:
                print(f"{model:28s} ERR {str(e)[:80]}")


if __name__ == "__main__":
    main()
