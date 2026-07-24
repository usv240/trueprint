"""Smoke tests for helpers that don't need B2/GMI credentials."""
import io
from PIL import Image
from backend.app import main as M
from backend.app import c2pa_sign as C


def test_cap_dimensions_downscales_and_preserves_small():
    big = io.BytesIO(); Image.new("RGB", (3000, 2000)).save(big, "JPEG")
    out = M._cap_dimensions(big.getvalue())
    assert max(Image.open(io.BytesIO(out)).size) <= M.MAX_DIM
    small = io.BytesIO(); Image.new("RGB", (200, 200)).save(small, "JPEG")
    same = small.getvalue()
    assert M._cap_dimensions(same) == same, "small images pass through unchanged"


def test_c2pa_manifest_declares_ai_edit():
    man = C.build_manifest(
        title="t", stats={"pct_original": 100, "pct_color_inferred": 10,
                          "pct_fabricated": 0, "mean_confidence": 0.8},
        models={"colorize": "x"}, master_sha256="abc", disclosure="d")
    labels = [a["label"] for a in man["assertions"]]
    assert "c2pa.actions" in labels
    assert any("trueprint" in l for l in labels)
    actions = next(a["data"]["actions"] for a in man["assertions"] if a["label"] == "c2pa.actions")
    assert any("TrainedAlgorithmicMedia" in a.get("digitalSourceType", "") for a in actions), \
        "must declare the AI edit (EU AI Act Art.50 marking)"


def test_health_and_samples_served():
    from starlette.testclient import TestClient
    c = TestClient(M.app)
    assert c.get("/api/health").status_code == 200
    r = c.get("/api/samples")
    assert r.status_code == 200 and isinstance(r.json(), list)
