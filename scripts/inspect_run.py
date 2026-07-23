from __future__ import annotations
import sys, io, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config
OUT = Path(__file__).resolve().parents[1] / "assets" / "_test_out"; OUT.mkdir(parents=True, exist_ok=True)


def _png():
    from PIL import Image, ImageDraw
    img = Image.new("L", (512, 512), 205); d = ImageDraw.Draw(img)
    d.ellipse((170, 120, 342, 330), fill=150); d.rectangle((120, 330, 392, 512), fill=95)
    d.line((0, 70, 512, 480), fill=25, width=4)
    b = io.BytesIO(); img.convert("RGB").save(b, "PNG"); return b.getvalue()


from genblaze_s3 import S3StorageBackend
from genblaze_gmicloud import GMICloudImageProvider
import genblaze as g

be = S3StorageBackend.for_backblaze(config.B2_BUCKET, region=config.B2_REGION,
                                    key_id=config.B2_KEY_ID, app_key=config.B2_APP_KEY, preflight=True)
be.put("trueprint/_healthcheck/insp.png", _png(), content_type="image/png")
url = be.presigned_get_url("trueprint/_healthcheck/insp.png", expires_in=3600)
url = url if isinstance(url, str) else getattr(url, "url", str(url))

prov = GMICloudImageProvider(api_key=config.GMI_API_KEY, base_url=config.GMI_IMAGE_BASE_URL)
pipe = g.Pipeline("insp").step(prov, model=config.GMI_MODEL_RECOLOR,
                               prompt="Colorize this black-and-white photograph with natural, realistic colors.",
                               modality=g.Modality.IMAGE,
                               external_inputs=[g.Asset(url=url, media_type="image/png")])
res = pipe.run(timeout=240, raise_on_failure=False)
print("error_summary:", getattr(res, "error_summary", None))
print("failed_steps:", getattr(res, "failed_steps", None))
print("succeeded_steps:", getattr(res, "succeeded_steps", None))
run = getattr(res, "run", None)
print("run type:", type(run).__name__)
steps = getattr(run, "steps", []) or []
for i, s in enumerate(steps):
    print(f" step[{i}] model={getattr(s,'model',None)} status={getattr(s,'status',None)} err={getattr(s,'error',None)}")
    for a in (getattr(s, "assets", []) or []):
        u = getattr(a, "url", None)
        print("   asset:", getattr(a, "media_type", None), str(u)[:110])
        try:
            import httpx
            r = httpx.get(u, timeout=60)
            if r.status_code == 200:
                p = OUT / f"pipeline_colorized_{i}.png"; p.write_bytes(r.content)
                print("   SAVED", p.name, len(r.content), "bytes")
        except Exception as e:
            print("   dl err", e)
m = getattr(res, "manifest", None)
print("manifest type:", type(m).__name__ if m else None)
