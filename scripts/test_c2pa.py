"""Prove we can embed + read a real signed C2PA Content Credential in a restored image."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from c2pa import Builder, Reader, Signer, C2paSignerInfo, C2paSigningAlg

ROOT = Path(__file__).resolve().parents[1]
CERT = ROOT / "backend" / "certs" / "dev_cert.pem"
KEY = ROOT / "backend" / "certs" / "dev_key.pem"
SRC = ROOT / "assets" / "_test_out" / "pipe_restored.png"
DST = ROOT / "assets" / "_test_out" / "pipe_restored_c2pa.png"

AI = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
CAPTURE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"

manifest = {
    "claim_generator_info": [{"name": "Trueprint", "version": "0.1"}],
    "title": "Restored: Abraham Lincoln (1863)",
    "format": "image/png",
    "assertions": [
        {"label": "c2pa.actions", "data": {"actions": [
            {"action": "c2pa.opened", "digitalSourceType": CAPTURE},
            {"action": "c2pa.color_adjustments",
             "softwareAgent": {"name": "gpt-image-2-edit"},
             "digitalSourceType": AI},
        ]}},
        {"label": "cawg.training-mining", "data": {"entries": {
            "cawg.ai_generative_training": {"use": "notAllowed"}}}},
        {"label": "org.trueprint.provenance", "data": {
            "structure_preserved_pct": 100.0, "color_inferred_pct": 11.7,
            "mean_confidence": 0.77,
            "disclosure": "Structure preserved (luminance locked); all color AI-inferred.",
            "models": {"vision": "google/gemini-3.6-flash", "colorize": "gpt-image-2-edit"},
            "master_sha256": "a1b7…9f3c", "storage": "backblaze-b2",
        }},
    ],
}

signer_info = C2paSignerInfo(
    alg=C2paSigningAlg.ES256,
    sign_cert=CERT.read_bytes(),
    private_key=KEY.read_bytes(),
    ta_url=b"http://timestamp.digicert.com",
)
signer = Signer.from_info(signer_info)

if DST.exists():
    DST.unlink()
with Builder(json.dumps(manifest)) as b:
    b.sign_file(str(SRC), str(DST), signer)
print("signed ->", DST.name, DST.stat().st_size, "bytes")

# read it back
reader = Reader(str(DST))
data = json.loads(reader.json())
active = data.get("active_manifest")
m = data["manifests"][active]
print("claim_generator:", m.get("claim_generator") or m.get("claim_generator_info"))
labels = [a["label"] for a in m.get("assertions", [])]
print("assertions:", labels)
acts = next((a["data"]["actions"] for a in m["assertions"] if a["label"] == "c2pa.actions"), [])
print("AI action digitalSourceType:", [x.get("digitalSourceType", "").split("/")[-1] for x in acts])
print("validation:", data.get("validation_state") or data.get("validation_status", "n/a"))
