"""Refresh cached restorations with the newest metadata (analysis, faithfulness
verification, disclosure, C2PA) — Gemini/C2PA only, NO image generation. Cheap."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.storage import B2Store, sha256_hex
from backend.app.pipeline import RestorePipeline
from backend.app.authenticity import Authenticity
from backend.app import c2pa_sign

store = B2Store()
pipe = RestorePipeline()
cache = json.loads(store.get("index/precache.json"))
A_FIELDS = ("pct_original", "pct_enhanced", "pct_fabricated", "pct_color_inferred", "mean_confidence")

for name, e in cache.items():
    aid, rid = e["asset_id"], e["run_id"]
    base = f"derivatives/{aid}/{rid}"
    man = json.loads(store.get(f"{base}/manifest.json"))
    master_url = store.url(man["master"]["b2_key"])
    restored_url = store.url(f"{base}/restored.png")

    analysis = pipe._vision_analyze(master_url)
    verification = pipe._verify_faithfulness(master_url, restored_url)
    stats = Authenticity(**{k: man["authenticity"].get(k) for k in A_FIELDS}, notes=[])
    disclosure = pipe._disclosure(stats, analysis)

    man["analysis"] = analysis
    man["verification"] = verification
    man["disclosure_statement"] = disclosure

    # re-sign C2PA with the refreshed disclosure
    restored = store.get(f"{base}/restored.png")
    c2pa_man = c2pa_sign.build_manifest(
        title=f"Restored: {name}", stats=man["authenticity"],
        models={"vision": man["providers"]["vision"], "colorize": man["providers"]["colorize"]},
        master_sha256=man["master"]["sha256"], disclosure=disclosure)
    signed, status = c2pa_sign.sign_png(restored, c2pa_man)
    if signed:
        store.put_derivative(aid, rid, "restored_c2pa.png", signed, "image/png")
        man["c2pa"] = {"embedded": True, "status": status, "standard": "C2PA 2.x",
                       "signer": "self-signed dev cert (untrusted by design; production uses a trust-list CA)",
                       "ai_marking": "compositeWithTrainedAlgorithmicMedia (EU AI Act Article 50)",
                       "b2_key": f"{base}/restored_c2pa.png"}

    m2 = {k: v for k, v in man.items() if k != "manifest_sha256"}
    man["manifest_sha256"] = sha256_hex(json.dumps(m2, sort_keys=True, default=str).encode())
    store.put_derivative(aid, rid, "manifest.json",
                         json.dumps(man, indent=2, default=str).encode(), "application/json")
    print(f"{name}: verify={verification.get('passed')} score={verification.get('score')} "
          f"| documented={len(analysis.get('documented_colors') or [])} "
          f"| uncertain={len(analysis.get('uncertain_colors') or [])}")
print("done")
