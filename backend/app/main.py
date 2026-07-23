"""Trueprint FastAPI backend.

Serves the landing + app UI and the restoration/verification API.
Long-running restorations run in a background thread; the browser follows
progress over Server-Sent Events.
"""
from __future__ import annotations
import io, json, threading, uuid, time
from pathlib import Path
from queue import Queue, Empty

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .storage import B2Store, sha256_hex
from .pipeline import RestorePipeline

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "assets" / "samples"
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Trueprint", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---- lazy singletons (avoid B2/GMI preflight at import time) ----
_pipe: RestorePipeline | None = None
_store: B2Store | None = None


def pipeline() -> RestorePipeline:
    global _pipe
    if _pipe is None:
        _pipe = RestorePipeline()
    return _pipe


def store() -> B2Store:
    global _store
    if _store is None:
        _store = B2Store()
    return _store


# ---- in-memory job registry (single-instance; fine for the demo) ----
JOBS: dict[str, dict] = {}


def _run_job(job_id: str, image_bytes: bytes, filename: str, samples: int) -> None:
    job = JOBS[job_id]
    q: Queue = job["queue"]

    def progress(ev: dict) -> None:
        q.put({"type": "progress", **ev})

    try:
        result = pipeline().run(image_bytes, filename, progress=progress, samples=samples)
        job["result"] = result
        q.put({"type": "done", "asset_id": result["asset_id"], "run_id": result["run_id"]})
    except Exception as e:  # surface a clean error to the client
        job["error"] = str(e)
        q.put({"type": "error", "message": str(e)[:300]})
    finally:
        q.put({"type": "_eof"})


# ------------------------------------------------------------------ API
@app.get("/api/health")
def health():
    return {"ok": True, "bucket": config.B2_BUCKET, "vision": config.GMI_MODEL_VISION,
            "colorize": config.GMI_MODEL_RECOLOR}


def _precache_map() -> dict:
    try:
        return json.loads(store().get("index/precache.json"))
    except Exception:
        return {}


def _result_payload(asset_id: str, run_id: str) -> dict:
    base = f"derivatives/{asset_id}/{run_id}"
    manifest = json.loads(store().get(f"{base}/manifest.json"))
    auth = manifest.get("authenticity", {})
    stats = {k: auth.get(k) for k in ("pct_original", "pct_enhanced", "pct_fabricated",
                                      "pct_color_inferred", "mean_confidence")}
    return {
        "asset_id": asset_id, "run_id": run_id, "stats": stats,
        "analysis": manifest.get("analysis", {}),
        "disclosure": manifest.get("disclosure_statement", ""),
        "manifest_sha256": manifest.get("manifest_sha256", ""),
        "manifest": manifest,
        "urls": {
            "master": store().url(manifest["master"]["b2_key"]),
            "restored": store().url(f"{base}/restored.png"),
            "authenticity_map": store().url(f"{base}/authenticity_map.png"),
            "confidence": store().url(f"{base}/confidence.png"),
            "manifest": store().url(f"{base}/manifest.json"),
        },
    }


@app.get("/api/samples")
def samples():
    cache = _precache_map()
    out = []
    for p in sorted(SAMPLES.glob("*.jpg")):
        out.append({"name": p.name, "url": f"/api/sample/{p.name}",
                    "label": p.stem.replace("_", " ").title(),
                    "cached": p.name in cache})
    return out


@app.get("/api/cached/{name}")
def cached(name: str):
    entry = _precache_map().get(name)
    if not entry:
        raise HTTPException(404, "no cached result")
    return _result_payload(entry["asset_id"], entry["run_id"])


@app.get("/api/sample/{name}")
def sample_img(name: str):
    p = (SAMPLES / name).resolve()
    if not str(p).startswith(str(SAMPLES.resolve())) or not p.exists():
        raise HTTPException(404, "sample not found")
    return FileResponse(p)


@app.post("/api/restore")
async def restore(file: UploadFile | None = File(None), sample: str | None = Form(None),
                  samples: int = Form(2)):
    if sample:
        p = (SAMPLES / sample).resolve()
        if not str(p).startswith(str(SAMPLES.resolve())) or not p.exists():
            raise HTTPException(404, "sample not found")
        data, filename = p.read_bytes(), sample
    elif file is not None:
        data, filename = await file.read(), (file.filename or "upload.jpg")
    else:
        raise HTTPException(400, "provide a file or a sample name")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "image too large (max 25MB)")

    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"queue": Queue(), "result": None, "error": None, "created": time.time()}
    threading.Thread(target=_run_job, args=(job_id, data, filename, max(1, min(3, samples))),
                     daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/restore/stream/{job_id}")
def restore_stream(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "unknown job")

    def gen():
        q: Queue = job["queue"]
        while True:
            try:
                ev = q.get(timeout=30)
            except Empty:
                yield ": keepalive\n\n"
                continue
            if ev.get("type") == "_eof":
                if job.get("result"):
                    yield f"event: result\ndata: {json.dumps(job['result'])}\n\n"
                break
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/result/{asset_id}/{run_id}")
def result(asset_id: str, run_id: str):
    try:
        return _result_payload(asset_id, run_id)
    except Exception:
        raise HTTPException(404, "result not found")


@app.post("/api/verify")
async def verify(file: UploadFile = File(...)):
    """Tamper check: hash the uploaded file, look it up in the B2 catalog."""
    data = await file.read()
    digest = sha256_hex(data)
    try:
        catalog = store().get("index/catalog.jsonl").decode().splitlines()
    except Exception:
        catalog = []
    for line in catalog:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if digest in (row.get("derivative_sha256"), row.get("master_sha256")):
            base = f"derivatives/{row['asset_id']}/{row['run_id']}"
            manifest = json.loads(store().get(f"{base}/manifest.json"))
            kind = "restored derivative" if digest == row.get("derivative_sha256") else "original master"
            return {"verified": True, "kind": kind, "sha256": digest,
                    "asset_id": row["asset_id"], "run_id": row["run_id"], "manifest": manifest}
    return {"verified": False, "sha256": digest,
            "message": "No matching record. This file was not produced by Trueprint, or it has been modified."}


# ------------------------------------------------------------------ static
@app.get("/", response_class=HTMLResponse)
def index():
    f = FRONTEND / "index.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>Trueprint</h1>"


@app.get("/app", response_class=HTMLResponse)
def app_page():
    f = FRONTEND / "app.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>app.html missing</h1>"


@app.get("/verify", response_class=HTMLResponse)
def verify_page():
    f = FRONTEND / "app.html"
    return f.read_text(encoding="utf-8") if f.exists() else "<h1>app.html missing</h1>"
