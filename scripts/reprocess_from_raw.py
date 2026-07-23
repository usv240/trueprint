"""Rebuild cached restorations from stored raw colorize outputs (NO image gen).
Applies the latest authenticity engine (ghost-fixed recombine), damage repair,
faithfulness verification, disclosure, and C2PA signing; overwrites derivatives + manifest.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.storage import B2Store, sha256_hex
from backend.app import authenticity as A
from backend.app.pipeline import RestorePipeline
from backend.app import c2pa_sign

store = B2Store()
pipe = RestorePipeline()
cache = json.loads(store.get("index/precache.json"))

for name, e in cache.items():
    aid, rid = e["asset_id"], e["run_id"]
    base = f"derivatives/{aid}/{rid}"
    man = json.loads(store.get(f"{base}/manifest.json"))
    master_key = man["master"]["b2_key"]
    original = A.load_rgb(store.get(master_key))
    ai_samples = []
    for i in (0, 1):
        try:
            ai_samples.append(A.load_rgb(store.get(f"{base}/steps/colorize_{i}/raw.png")))
        except Exception:
            pass
    if not ai_samples:
        print(name, "no raw colorize artifacts — skip"); continue

    repaired, mask = A.repair_damage(original)
    fab = {"damage_repair": mask} if (mask > 0).sum() > 50 else None
    final = A.colorize_recombine(repaired, ai_samples[0])          # ghost-fixed
    confidence, mean_conf = A.color_confidence(original, ai_samples)
    cls, stats = A.classify(original, final, confidence=confidence, fabricated_regions=fab)

    restored_png = A.to_png(final)
    store.put_derivative(aid, rid, "restored.png", restored_png, "image/png")
    store.put_derivative(aid, rid, "authenticity_map.png", A.render_overlay(original, cls), "image/png")
    store.put_derivative(aid, rid, "confidence.png", A.render_confidence(original, confidence), "image/png")

    master_url = store.url(master_key)
    restored_url = store.url(f"{base}/restored.png")
    analysis = pipe._vision_analyze(master_url)
    verification = pipe._verify_faithfulness(master_url, restored_url)
    disclosure = pipe._disclosure(stats, analysis)

    man["authenticity"] = {**stats.to_dict(),
                           "map": f"{base}/authenticity_map.png", "confidence": f"{base}/confidence.png"}
    man["derivative"] = {"sha256": sha256_hex(restored_png), "b2_key": f"{base}/restored.png"}
    man["analysis"] = analysis
    man["verification"] = verification
    man["disclosure_statement"] = disclosure

    c2pa_man = c2pa_sign.build_manifest(
        title=f"Restored: {name}", stats=man["authenticity"],
        models={"vision": man["providers"]["vision"], "colorize": man["providers"]["colorize"]},
        master_sha256=man["master"]["sha256"], disclosure=disclosure)
    signed, status = c2pa_sign.sign_png(restored_png, c2pa_man)
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
          f"color={stats.pct_color_inferred}% conf={stats.mean_confidence}")
print("done")
