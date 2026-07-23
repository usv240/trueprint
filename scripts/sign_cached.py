"""Retro-sign cached restorations with C2PA + update their manifests (zero API cost)."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.storage import B2Store, sha256_hex
from backend.app import c2pa_sign

store = B2Store()
cache = json.loads(store.get("index/precache.json"))
for name, e in cache.items():
    aid, rid = e["asset_id"], e["run_id"]
    base = f"derivatives/{aid}/{rid}"
    manifest = json.loads(store.get(f"{base}/manifest.json"))
    restored = store.get(f"{base}/restored.png")
    stats = manifest["authenticity"]
    models = {"vision": manifest["providers"]["vision"], "colorize": manifest["providers"]["colorize"]}
    c2pa_man = c2pa_sign.build_manifest(
        title=f"Restored: {name}", stats=stats, models=models,
        master_sha256=manifest["master"]["sha256"], disclosure=manifest.get("disclosure_statement", ""))
    signed, status = c2pa_sign.sign_png(restored, c2pa_man)
    if not signed:
        print(name, "SIGN FAILED:", status); continue
    store.put_derivative(aid, rid, "restored_c2pa.png", signed, "image/png")
    manifest["c2pa"] = {
        "embedded": True, "status": status, "standard": "C2PA 2.x",
        "signer": "self-signed dev cert (untrusted by design; production uses a trust-list CA)",
        "ai_marking": "compositeWithTrainedAlgorithmicMedia (EU AI Act Article 50)",
        "b2_key": f"{base}/restored_c2pa.png"}
    m2 = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    manifest["manifest_sha256"] = sha256_hex(json.dumps(m2, sort_keys=True, default=str).encode())
    store.put_derivative(aid, rid, "manifest.json",
                         json.dumps(manifest, indent=2, default=str).encode(), "application/json")
    # verify round-trip
    cred = c2pa_sign.read_credential(signed)
    print(f"{name}: signed ({len(signed)}b) · validation {cred['validation_state']} · "
          f"actions {[a['action'] for a in cred['actions']]}")
print("done")
