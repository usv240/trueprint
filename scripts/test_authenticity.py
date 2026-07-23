"""Offline test of the authenticity engine (no API calls)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import authenticity as A

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "_test_out"; OUT.mkdir(parents=True, exist_ok=True)

orig = A.load_rgb((ROOT / "assets/samples/migrant_mother.jpg").read_bytes())
gray = cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY)

# two *different* synthetic "colorizers" to create genuine disagreement
synthA = cv2.cvtColor(cv2.applyColorMap(gray, cv2.COLORMAP_AUTUMN), cv2.COLOR_BGR2RGB)
synthB = cv2.cvtColor(cv2.applyColorMap(gray, cv2.COLORMAP_PINK), cv2.COLOR_BGR2RGB)

recombined = A.colorize_recombine(orig, synthA)
conf, meanc = A.color_confidence(orig, [synthA, synthB])
cls, stats = A.classify(orig, recombined, confidence=conf)

(OUT / "auth_recolored.png").write_bytes(A.to_png(recombined))
(OUT / "auth_overlay.png").write_bytes(A.render_overlay(orig, cls))
(OUT / "auth_confidence.png").write_bytes(A.render_confidence(orig, conf))
(OUT / "auth_damage.png").write_bytes(A.to_png(cv2.cvtColor(A.detect_damage(orig), cv2.COLOR_GRAY2RGB)))

print("image:", orig.shape)
print("mean confidence:", round(meanc, 3))
print("stats:", stats.to_dict())
print("saved: auth_recolored / auth_overlay / auth_confidence / auth_damage .png")
