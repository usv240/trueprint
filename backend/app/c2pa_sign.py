"""Embed real, signed C2PA Content Credentials into restored images.

Turns Trueprint's provenance into an industry-standard, verifiable credential
(readable in Adobe Content Credentials / any C2PA tool) and declares the AI color
edit as `compositeWithTrainedAlgorithmicMedia` — the EU AI Act Article 50
machine-readable AI marking. Zero API cost.

The signing cert is a self-provisioned, self-signed **dev** cert (no trust-list
membership) — so a strict verifier reports the *signer* as untrusted, which we
disclose honestly. A production deployment swaps in a CA cert on the C2PA trust list.
"""
from __future__ import annotations
import io, json, os, datetime
from pathlib import Path

CERTS = Path(__file__).resolve().parents[2] / "backend" / "certs"
CERT_PEM = CERTS / "dev_cert.pem"
KEY_PEM = CERTS / "dev_key.pem"
TSA_URL = os.getenv("C2PA_TSA_URL", "http://timestamp.digicert.com").encode()

IPTC = "http://cv.iptc.org/newscodes/digitalsourcetype/"
AI_EDIT = IPTC + "compositeWithTrainedAlgorithmicMedia"
CAPTURE = IPTC + "digitalCapture"


def ensure_dev_cert() -> tuple[bytes, bytes]:
    """Return (cert_pem, key_pem), generating a self-signed dev cert on first use."""
    if CERT_PEM.exists() and KEY_PEM.exists():
        return CERT_PEM.read_bytes(), KEY_PEM.read_bytes()
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    CERTS.mkdir(parents=True, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Trueprint Dev (self-signed, untrusted)"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Trueprint"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                           key_encipherment=False, data_encipherment=False, key_agreement=False,
                           key_cert_sign=False, crl_sign=False, encipher_only=False,
                           decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=True)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
            .sign(key, hashes.SHA256()))
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(serialization.Encoding.PEM,
                                serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
    CERT_PEM.write_bytes(cert_pem); KEY_PEM.write_bytes(key_pem)
    return cert_pem, key_pem


def build_manifest(*, title: str, stats: dict, models: dict, master_sha256: str,
                   disclosure: str, declined: bool = False) -> dict:
    color_source = CAPTURE if declined else AI_EDIT
    actions = [{"action": "c2pa.opened", "digitalSourceType": CAPTURE}]
    if not declined:
        actions.append({"action": "c2pa.color_adjustments",
                        "softwareAgent": {"name": models.get("colorize", "ai-image-model")},
                        "digitalSourceType": color_source})
    return {
        "claim_generator_info": [{"name": "Trueprint", "version": "0.1"}],
        "title": title, "format": "image/png",
        "assertions": [
            {"label": "c2pa.actions", "data": {"actions": actions}},
            {"label": "cawg.training-mining",
             "data": {"entries": {"cawg.ai_generative_training": {"use": "notAllowed"}}}},
            {"label": "org.trueprint.provenance", "data": {
                "structure_preserved_pct": stats.get("pct_original"),
                "color_inferred_pct": stats.get("pct_color_inferred"),
                "fabricated_structure_pct": stats.get("pct_fabricated"),
                "mean_confidence": stats.get("mean_confidence"),
                "disclosure": disclosure,
                "models": models, "master_sha256": master_sha256,
                "storage": "backblaze-b2",
                "note": "Structure luminance-locked to the original; all color is AI-inferred.",
            }},
        ],
    }


def sign_png(png_bytes: bytes, manifest: dict) -> tuple[bytes | None, str]:
    """Best-effort sign. Returns (signed_bytes | None, status_string)."""
    try:
        from c2pa import Builder, Signer, C2paSignerInfo, C2paSigningAlg
        cert, key = ensure_dev_cert()
        signer = Signer.from_info(C2paSignerInfo(
            alg=C2paSigningAlg.ES256, sign_cert=cert, private_key=key, ta_url=TSA_URL))
        src, dst = io.BytesIO(png_bytes), io.BytesIO()
        with Builder(json.dumps(manifest)) as b:
            b.sign(signer, "image/png", src, dst)
        return dst.getvalue(), "signed (self-signed dev cert; signer untrusted by design)"
    except Exception as e:
        return None, f"c2pa signing skipped: {str(e)[:160]}"


def read_credential(img_bytes: bytes, mime: str = "image/png") -> dict | None:
    """Extract an embedded C2PA credential, if any."""
    try:
        from c2pa import Reader
        with Reader(mime, io.BytesIO(img_bytes)) as r:
            data = json.loads(r.json())
        active = data.get("active_manifest")
        m = (data.get("manifests") or {}).get(active, {}) if active else {}
        actions = []
        for a in m.get("assertions", []):
            if a["label"].startswith("c2pa.actions"):
                actions = [{"action": x.get("action"),
                            "ai": x.get("digitalSourceType", "").endswith(("trainedAlgorithmicMedia",
                                  "compositeWithTrainedAlgorithmicMedia"))}
                           for x in a["data"].get("actions", [])]
        tp = next((a["data"] for a in m.get("assertions", [])
                   if a["label"] == "org.trueprint.provenance"), None)
        return {
            "present": True,
            "validation_state": data.get("validation_state"),
            "claim_generator": m.get("claim_generator") or m.get("claim_generator_info"),
            "title": m.get("title"),
            "actions": actions,
            "trueprint": tp,
        }
    except Exception:
        return None
