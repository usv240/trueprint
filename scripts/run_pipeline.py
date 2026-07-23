"""Run the full Trueprint Phase 1 pipeline on a sample photo."""
from __future__ import annotations
import sys, json
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.pipeline import RestorePipeline

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "_test_out"; OUT.mkdir(parents=True, exist_ok=True)
sample = ROOT / "assets/samples/lincoln.jpg"   # adult subject: reliable through gpt-image-2 moderation


def prog(ev): print("  •", ev.get("step"), ev.get("status"), ev.get("model") or "")


res = RestorePipeline().run(sample.read_bytes(), sample.name, progress=prog, samples=2)
print("\n=== RESULT ===")
print("asset_id:", res["asset_id"], "run_id:", res["run_id"])
print("stats:", json.dumps(res["stats"]))
print("disclosure:", res["disclosure"])
print("manifest_sha256:", res["manifest_sha256"])
print("analysis:", json.dumps(res.get("analysis", {}))[:300])
for name in ("restored", "authenticity_map", "confidence"):
    try:
        data = httpx.get(res["urls"][name], timeout=90).content
        p = OUT / f"pipe_{name}.png"; p.write_bytes(data)
        print(f"saved {p.name} ({len(data)} bytes)")
    except Exception as e:
        print("dl err", name, e)
print("\nB2 manifest url:", res["urls"]["manifest"][:100], "...")
