"""Full raw GMI request-queue generation: submit -> poll -> download.
Proves end-to-end media generation and captures the working payload + polling shape.
"""
from __future__ import annotations
import sys, io, time, json
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config

OUT = Path(__file__).resolve().parents[1] / "assets" / "_test_out"
OUT.mkdir(parents=True, exist_ok=True)
QUEUE = config.GMI_IMAGE_BASE_URL  # .../ie/requestqueue/apikey


def bw_png() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("L", (512, 512), 205); d = ImageDraw.Draw(img)
    d.ellipse((170, 120, 342, 330), fill=150)
    d.rectangle((120, 330, 392, 512), fill=95)
    d.line((0, 70, 512, 480), fill=25, width=4)
    buf = io.BytesIO(); img.convert("RGB").save(buf, "PNG"); return buf.getvalue()


def presign() -> str:
    from genblaze_s3 import S3StorageBackend
    be = S3StorageBackend.for_backblaze(config.B2_BUCKET, region=config.B2_REGION,
                                        key_id=config.B2_KEY_ID, app_key=config.B2_APP_KEY, preflight=True)
    key = "trueprint/_healthcheck/raw_src.png"
    be.put(key, bw_png(), content_type="image/png")
    url = be.presigned_get_url(key, expires_in=3600)
    return url if isinstance(url, str) else getattr(url, "url", str(url))


def run(model: str, payload: dict) -> None:
    h = {"Authorization": f"Bearer {config.GMI_API_KEY}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60) as c:
        print(f"\n--- submit {model} ---  payload keys: {list(payload)}")
        r = c.post(f"{QUEUE}/requests", headers=h, json={"model": model, "payload": payload})
        print("submit HTTP", r.status_code, r.text[:200])
        if r.status_code >= 300:
            return
        body = r.json()
        rid = body.get("request_id") or body.get("id") or body.get("data", {}).get("request_id")
        print("request_id:", rid)
        if not rid:
            print("full submit body:", json.dumps(body)[:400]); return
        # poll
        for i in range(60):
            time.sleep(4)
            pr = c.get(f"{QUEUE}/requests/{rid}", headers=h)
            if pr.status_code >= 300:
                print("poll HTTP", pr.status_code, pr.text[:200]); return
            d = pr.json()
            status = (d.get("status") or d.get("state") or d.get("data", {}).get("status") or "").lower()
            print(f"  [{i}] status={status!r}")
            if status in ("succeeded", "success", "completed", "done", "finished"):
                txt = json.dumps(d)
                print("  RESULT keys:", list(d.keys()))
                # find any image url in the response
                import re
                urls = re.findall(r'https?://[^\s\"\\]+\.(?:png|jpg|jpeg|webp)', txt)
                print("  image urls:", urls[:3])
                for j, u in enumerate(urls[:2]):
                    try:
                        img = httpx.get(u, timeout=60)
                        if img.status_code == 200:
                            p = OUT / f"raw_{model.replace('/','_')}_{j}.png"
                            p.write_bytes(img.content); print("  saved", p.name, len(img.content), "bytes")
                    except Exception as e:
                        print("  dl err", e)
                if not urls:
                    print("  full result:", txt[:600])
                return
            if status in ("failed", "error", "cancelled", "canceled"):
                print("  FAILED:", json.dumps(d)[:400]); return
        print("  timed out polling")


if __name__ == "__main__":
    url = presign()
    print("source URL:", url[:90], "...")
    # seededit: instruction i2i (prompt+image) — ideal for colorize
    run(config.GMI_MODEL_RESTORE, {
        "prompt": "Colorize this black-and-white photograph with natural, realistic colors. Keep all content and composition unchanged.",
        "image": url,
    })
