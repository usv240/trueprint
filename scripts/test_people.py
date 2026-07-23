"""Which i2i models will actually process a historical people-photo?"""
from __future__ import annotations
import sys, time, json, re
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config
from backend.app.storage import B2Store

OUT = Path(__file__).resolve().parents[1] / "assets" / "_test_out"; OUT.mkdir(parents=True, exist_ok=True)
Q = config.GMI_IMAGE_BASE_URL
store = B2Store()
img = (Path(__file__).resolve().parents[1] / "assets/samples/migrant_mother.jpg").read_bytes()
store.put("trueprint/_healthcheck/mm.png", img, content_type="image/jpeg")
url = store.url("trueprint/_healthcheck/mm.png", expires_in=3600)
P = "Colorize this black-and-white photograph with natural, realistic, period-accurate colors. Keep all detail."

cases = [
    ("bria-fibo-restore", {"image": url}),
    ("hunyuan-image-to-image", {"image": url, "prompt": P}),
    ("bria-genfill", {"image": url, "prompt": P, "mask": url}),
    ("gpt-image-2-edit", {"image": url, "prompt": P}),
]
h = {"Authorization": f"Bearer {config.GMI_API_KEY}", "Content-Type": "application/json"}
with httpx.Client(timeout=90) as c:
    for model, payload in cases:
        try:
            r = c.post(f"{Q}/requests", headers=h, json={"model": model, "payload": payload})
            d = {}
            try: d = r.json()
            except Exception: pass
            status = (d.get("status") or "").lower()
            rid = d.get("request_id") or d.get("id")
            # poll if pending
            for _ in range(20):
                if r.status_code >= 300 or status in ("success", "succeeded", "completed", "failed", "error"):
                    break
                if not rid:
                    break
                time.sleep(4)
                pr = c.get(f"{Q}/requests/{rid}", headers=h); d = pr.json()
                status = (d.get("status") or "").lower()
            txt = json.dumps(d)
            urls = re.findall(r'https?://[^\s"\\]+\.(?:png|jpg|jpeg|webp)', txt)
            verdict = f"HTTP{r.status_code} status={status!r}"
            if urls:
                out = httpx.get(urls[0], timeout=90).content
                p = OUT / f"people_{model}.png"; p.write_bytes(out)
                verdict += f"  OK -> {p.name} ({len(out)}b)"
            else:
                verdict += "  " + txt[:150]
            print(f"{model:26s} {verdict}")
        except Exception as e:
            print(f"{model:26s} ERR {str(e)[:100]}")
