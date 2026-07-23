"""Pre-run the pipeline on reliable sample photos and record a cache map on B2,
so the live demo serves instant results (with a 'run live' option still available)."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.pipeline import RestorePipeline
from backend.app.storage import B2Store

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "assets" / "samples"
# adult subjects that pass image-model moderation reliably
TO_CACHE = ["lincoln.jpg", "portrait2.jpg"]

store = B2Store()
try:
    cache = json.loads(store.get("index/precache.json"))
except Exception:
    cache = {}

pipe = RestorePipeline()
for name in TO_CACHE:
    p = SAMPLES / name
    if not p.exists():
        print("skip (missing):", name); continue
    print("caching", name, "…")
    res = pipe.run(p.read_bytes(), name, samples=2)
    cache[name] = {"asset_id": res["asset_id"], "run_id": res["run_id"]}
    store.put("index/precache.json", json.dumps(cache, indent=2).encode(), "application/json")
    print("  ->", cache[name], "| color_inferred", res["stats"].get("pct_color_inferred"),
          "| conf", res["stats"].get("mean_confidence"))

print("\nprecache map:", json.dumps(cache, indent=2))
