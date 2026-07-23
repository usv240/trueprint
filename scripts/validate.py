"""Validate live B2 + GMI connections using the real Genblaze SDK.
Run: ./.venv/Scripts/python scripts/validate.py
"""
from __future__ import annotations
import sys, inspect, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config


def hr(t): print("\n" + "=" * 8, t, "=" * 8)


def validate_b2() -> bool:
    hr("Backblaze B2")
    config.require_b2()
    from genblaze_s3 import S3StorageBackend
    print("put signature:", inspect.signature(S3StorageBackend.put))
    be = S3StorageBackend.for_backblaze(
        config.B2_BUCKET,
        region=config.B2_REGION,
        key_id=config.B2_KEY_ID,
        app_key=config.B2_APP_KEY,
        preflight=True,
    )
    key = "trueprint/_healthcheck/hello.txt"
    data = b"trueprint b2 ok"
    try:
        be.put(key, data, content_type="text/plain")
    except TypeError:
        be.put(key, data)  # fallback if signature differs
    exists = be.exists(key)
    got = be.get(key)
    got_bytes = got if isinstance(got, (bytes, bytearray)) else getattr(got, "data", got)
    print("exists:", exists, "| round-trip match:", bytes(got_bytes) == data)
    be.delete(key)
    print("cleanup: deleted test object")
    print("B2 OK ✅")
    return True


def validate_gmi() -> bool:
    hr("GMI Cloud")
    config.require_gmi()
    from genblaze_gmicloud import GMICloudImageProvider
    p = GMICloudImageProvider(api_key=config.GMI_API_KEY, base_url=config.GMI_BASE_URL)
    wanted = [config.GMI_MODEL_INPAINT, config.GMI_MODEL_RESTORE,
              config.GMI_MODEL_RECOLOR, config.GMI_MODEL_COLORIZE_ALT,
              config.GMI_MODEL_COLORIZE_ALT2]
    # try to enumerate available image models
    models = None
    for meth in ("list_models", "discover_models"):
        if hasattr(p, meth):
            try:
                models = list(getattr(p, meth)())
                print(f"{meth}() -> {len(models)} models")
                break
            except Exception as e:
                print(f"{meth}() failed: {e}")
    if models:
        ids = {getattr(m, "id", getattr(m, "model", str(m))) for m in models}
        sample = list(ids)[:25]
        print("sample image model ids:", sample)
        for w in wanted:
            print(f"  {'✅' if w in ids else '❓'} {w}")
    else:
        # fall back to probing each model
        for w in wanted:
            try:
                r = p.probe_model(w)
                print(f"  probe {w}: {getattr(r,'status',r)}")
            except Exception as e:
                print(f"  probe {w}: ERR {e}")
    print("GMI reachable ✅")
    return True


if __name__ == "__main__":
    ok = True
    for fn in (validate_b2, validate_gmi):
        try:
            fn()
        except Exception:
            ok = False
            print("FAILED:")
            traceback.print_exc()
    print("\nRESULT:", "ALL GOOD ✅" if ok else "SOME CHECKS FAILED ❌")
    sys.exit(0 if ok else 1)
