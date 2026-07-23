"""Real end-to-end image-to-image test on GMI via Genblaze:
generate a B&W test image -> upload to B2 -> presign -> colorize -> inspect result.
Run: ./.venv/Scripts/python scripts/test_image.py
"""
from __future__ import annotations
import sys, io, inspect
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config

OUT = Path(__file__).resolve().parents[1] / "assets" / "_test_out"
OUT.mkdir(parents=True, exist_ok=True)


def make_bw_image() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("L", (512, 512), 210)
    d = ImageDraw.Draw(img)
    d.ellipse((160, 120, 352, 340), fill=150)          # a "face"
    d.rectangle((120, 340, 392, 512), fill=90)         # "shoulders"
    d.line((0, 60, 512, 500), fill=30, width=3)        # a "scratch"
    return img.convert("RGB")._repr_png_() if hasattr(Image, "_repr_png_") else _to_png(img)


def _to_png(img) -> bytes:
    buf = io.BytesIO(); img.convert("RGB").save(buf, format="PNG"); return buf.getvalue()


def main() -> int:
    config.require_b2(); config.require_gmi()
    from genblaze_s3 import S3StorageBackend
    from genblaze_gmicloud import GMICloudImageProvider
    import genblaze as g

    # 1) source image
    from PIL import Image, ImageDraw
    img = Image.new("L", (512, 512), 210); d = ImageDraw.Draw(img)
    d.ellipse((160, 120, 352, 340), fill=150); d.rectangle((120, 340, 392, 512), fill=90)
    d.line((0, 60, 512, 500), fill=30, width=3)
    src = _to_png(img)
    (OUT / "src_bw.png").write_bytes(src)
    print("made B&W source:", len(src), "bytes")

    # 2) upload to B2 + presign a public URL GMI can fetch
    be = S3StorageBackend.for_backblaze(config.B2_BUCKET, region=config.B2_REGION,
                                        key_id=config.B2_KEY_ID, app_key=config.B2_APP_KEY, preflight=True)
    key = "trueprint/_healthcheck/src_bw.png"
    be.put(key, src, content_type="image/png")
    presign = None
    for meth in ("presigned_get_url", "get_durable_url", "get_url"):
        if hasattr(be, meth):
            try:
                fn = getattr(be, meth)
                try: presign = fn(key, expires_in=3600)
                except TypeError:
                    try: presign = fn(key, 3600)
                    except TypeError: presign = fn(key)
                if presign: print(f"URL via {meth}: {str(presign)[:90]}..."); break
            except Exception as e:
                print(f"{meth} failed: {e}")
    if not presign:
        print("could not presign; abort"); return 1
    url = presign if isinstance(presign, str) else getattr(presign, "url", str(presign))

    # 3) run a real i2i colorize step (image provider uses the request-queue base_url)
    provider = GMICloudImageProvider(api_key=config.GMI_API_KEY, base_url=config.GMI_IMAGE_BASE_URL)
    asset = g.Asset(url=url, media_type="image/png")
    model = config.GMI_MODEL_RECOLOR  # gpt-image-2-edit (instruction i2i)
    print("invoking image model:", model)
    pipe = g.Pipeline("trueprint-imgtest").step(
        provider, model=model,
        prompt="Colorize this black-and-white photograph with natural, realistic colors. Do not change content.",
        modality=g.Modality.IMAGE,
        external_inputs=[asset],
    )
    result = pipe.run(timeout=240, raise_on_failure=False)
    print("PipelineResult type:", type(result).__name__)
    print("  attrs:", [a for a in dir(result) if not a.startswith('_')][:30])
    status = getattr(result, "status", None)
    print("  status:", status)

    # 4) extract output asset(s)
    assets = []
    for path in ("assets", "outputs", "output_assets"):
        v = getattr(result, path, None)
        if v: assets = list(v); break
    if not assets:
        steps = getattr(result, "steps", None) or []
        for s in steps:
            assets += list(getattr(s, "assets", []) or [])
            print("  step:", getattr(s, "model", "?"), getattr(s, "status", "?"),
                  "err=", getattr(s, "error", None))
    print("  output assets:", len(assets))
    for i, a in enumerate(assets):
        u = getattr(a, "url", None); print(f"   asset[{i}] {getattr(a,'media_type','?')} {str(u)[:100]}")
        try:
            import httpx
            r = httpx.get(u, timeout=60)
            if r.status_code == 200:
                (OUT / f"colorized_{i}.png").write_bytes(r.content)
                print(f"     saved colorized_{i}.png ({len(r.content)} bytes)")
        except Exception as e:
            print("     download err", e)
    return 0 if assets else 2


if __name__ == "__main__":
    raise SystemExit(main())
