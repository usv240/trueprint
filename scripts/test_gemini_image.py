"""Validate Google Gemini image i2i colorization as an independent 2nd provider."""
from __future__ import annotations
import sys, os, io, json, base64
from pathlib import Path
import httpx
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import config
from backend.app import authenticity as A

KEY = os.getenv("GOOGLE_API_KEY") or config._get("GOOGLE_API_KEY") if hasattr(config, "_get") else None
from dotenv import load_dotenv; load_dotenv(Path(__file__).resolve().parents[1] / ".env")
KEY = os.getenv("GOOGLE_API_KEY")
OUT = Path(__file__).resolve().parents[1] / "assets" / "_test_out"; OUT.mkdir(parents=True, exist_ok=True)

PROMPT = ("Colorize this black-and-white photograph with natural, realistic, period-accurate colors. "
          "Keep every detail and the exact composition unchanged. Output the full image.")


def b64_of(path: Path, max_w: int = 1024) -> tuple[str, str]:
    from PIL import Image
    img = Image.open(path).convert("RGB")
    if img.width > max_w:
        img = img.resize((max_w, int(img.height * max_w / img.width)))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


def colorize(model: str, path: Path):
    data, mime = b64_of(path)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}"
    body = {"contents": [{"parts": [
        {"text": PROMPT}, {"inline_data": {"mime_type": mime, "data": data}}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}}
    r = httpx.post(url, json=body, timeout=180)
    print(f"{model}: HTTP {r.status_code}")
    if r.status_code >= 300:
        print("  ", r.text[:250]); return None
    d = r.json()
    parts = d.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    for p in parts:
        idata = p.get("inline_data") or p.get("inlineData")
        if idata and idata.get("data"):
            raw = base64.b64decode(idata["data"])
            ai = A.load_rgb(raw)
            orig = A.load_rgb(path.read_bytes())
            out = OUT / f"gemini_{model.replace('.','_')}_{path.stem}.png"
            out.write_bytes(A.to_png(A.colorize_recombine(orig, ai)))
            print(f"   colorized -> {out.name} | ai size {ai.shape[:2]} | raw {len(raw)}b")
            return out
    print("   no image in response:", json.dumps(d)[:200]); return None


if __name__ == "__main__":
    print("key prefix:", (KEY or "")[:6], "len", len(KEY or ""))
    for model in ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]:
        colorize(model, Path("assets/samples/lincoln.jpg"))
