"""Generate AI 'historical-style' B&W images (clearly-labeled test cases)."""
from __future__ import annotations
import sys, json, re, time, io
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config
from PIL import Image

Q = config.GMI_IMAGE_BASE_URL
H = {"Authorization": f"Bearer {config.GMI_API_KEY}", "Content-Type": "application/json"}
SAMPLES = Path(__file__).resolve().parents[1] / "assets" / "samples"

JOBS = [
    ("aigen_portrait.jpg", "gpt-image-2-generate",
     "A black-and-white vintage studio portrait photograph of a fictional early-20th-century "
     "woman scientist, monochrome, soft studio lighting, 1920s photographic style, subtle film "
     "grain, plain studio backdrop. Not a real person."),
    ("aigen_street.jpg", "seedream-5.0-lite",
     "A black-and-white vintage photograph of a fictional 1910s city street with horse-drawn "
     "carriages and pedestrians, monochrome, documentary photographic style, subtle film grain."),
]


def submit(model, prompt):
    r = httpx.post(f"{Q}/requests", headers=H, json={"model": model, "payload": {"prompt": prompt}}, timeout=120)
    d = r.json() if r.status_code < 300 else {}
    rid = d.get("request_id") or d.get("id")
    status = (d.get("status") or "").lower()
    for _ in range(30):
        if r.status_code >= 300 or status in ("success", "succeeded", "completed", "failed", "error"):
            break
        if not rid:
            break
        time.sleep(4)
        d = httpx.get(f"{Q}/requests/{rid}", headers=H, timeout=60).json()
        status = (d.get("status") or "").lower()
    urls = re.findall(r'https?://[^\s"\\]+\.(?:png|jpg|jpeg|webp)', json.dumps(d))
    return urls[0] if urls else None


for name, model, prompt in JOBS:
    print(f"generating {name} via {model} ...")
    url = submit(model, prompt)
    if not url:
        print("  FAILED"); continue
    raw = httpx.get(url, timeout=90).content
    img = Image.open(io.BytesIO(raw)).convert("L")     # force true grayscale
    if max(img.size) > 1024:
        r = 1024 / max(img.size); img = img.resize((int(img.width * r), int(img.height * r)))
    img.convert("RGB").save(SAMPLES / name, "JPEG", quality=92)
    print(f"  saved {name} ({img.size})")
print("done")
