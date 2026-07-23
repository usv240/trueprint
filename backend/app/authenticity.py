"""Trueprint authenticity engine.

The core idea: because we *control* the compositing of each restoration step,
the authenticity map is recorded at generation time, not guessed afterward.

Key techniques
--------------
* **Luminance-locked colorization.** A grayscale master has no chroma. We take the
  AI model's *color* (LAB a,b channels) but keep the *original's luminance* (L).
  The result is structurally identical to the real photo, and the claim
  "100% of color is AI-inferred, structure is original" is literally true.
* **Multi-sample confidence.** Run colorization across independent samples/models
  and measure per-pixel color disagreement. Agreement => grounded inference;
  disagreement => the AI is guessing. This is the confidence heatmap.
* **Region classification.** Every pixel is ORIGINAL, ENHANCED, or FABRICATED,
  derived from measured luminance/chroma change, not vibes.
"""
from __future__ import annotations
import io
from dataclasses import dataclass, field, asdict
import numpy as np
import cv2
from PIL import Image

# class ids
ORIGINAL, ENHANCED, FABRICATED = 0, 1, 2
# overlay colors (RGB) — mirror the landing page palette
CLASS_RGB = {
    ORIGINAL:  (51, 194, 180),   # teal
    ENHANCED:  (228, 177, 78),   # amber
    FABRICATED:(240, 106, 66),   # vermilion
}


# ---------------------------------------------------------------- io helpers
def load_rgb(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def to_png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


def _resize_to(src: np.ndarray, h: int, w: int) -> np.ndarray:
    if src.shape[0] == h and src.shape[1] == w:
        return src
    return cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------- colorization core
def colorize_recombine(original_rgb: np.ndarray, ai_rgb: np.ndarray) -> np.ndarray:
    """Keep ORIGINAL luminance, borrow AI chroma. Output is structurally faithful."""
    h, w = original_rgb.shape[:2]
    ai = _resize_to(ai_rgb, h, w)
    orig_lab = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2LAB)
    ai_lab = cv2.cvtColor(ai, cv2.COLOR_RGB2LAB)
    out_lab = np.stack([orig_lab[:, :, 0], ai_lab[:, :, 1], ai_lab[:, :, 2]], axis=-1)
    return cv2.cvtColor(out_lab, cv2.COLOR_LAB2RGB)


def _ab(original_rgb: np.ndarray, ai_rgb: np.ndarray) -> np.ndarray:
    """The a,b chroma an AI proposed, aligned to the original's structure (float)."""
    h, w = original_rgb.shape[:2]
    ai_lab = cv2.cvtColor(_resize_to(ai_rgb, h, w), cv2.COLOR_RGB2LAB).astype(np.float32)
    return ai_lab[:, :, 1:3]  # (H,W,2)


def color_confidence(original_rgb: np.ndarray, ai_samples: list[np.ndarray]) -> tuple[np.ndarray, float]:
    """Per-pixel confidence in [0,1] from disagreement across colorizations.

    Disagreement = mean pairwise Euclidean distance in (a,b). 0 dist => confidence 1.
    """
    h, w = original_rgb.shape[:2]
    if len(ai_samples) < 2:
        return np.ones((h, w), np.float32), 1.0
    abs_ = [_ab(original_rgb, s) for s in ai_samples]
    # mean pairwise distance
    dists = []
    for i in range(len(abs_)):
        for j in range(i + 1, len(abs_)):
            dists.append(np.linalg.norm(abs_[i] - abs_[j], axis=-1))
    disagree = np.mean(dists, axis=0)  # (H,W), LAB units
    # map disagreement -> confidence. ~25 LAB units of ab-distance is a big disagreement.
    conf = np.clip(1.0 - disagree / 25.0, 0.0, 1.0).astype(np.float32)
    return conf, float(conf.mean())


# ------------------------------------------------------------- damage masks
def detect_damage(original_rgb: np.ndarray) -> np.ndarray:
    """Heuristic scratch/dust/tear mask via morphological black/top-hat. Returns 0/255 mask."""
    gray = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2GRAY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k)  # dark thin defects
    tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k)      # bright thin defects
    defect = cv2.max(blackhat, tophat)
    _, mask = cv2.threshold(defect, 38, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    return mask


# -------------------------------------------------------- authenticity map
@dataclass
class Authenticity:
    pct_original: float
    pct_enhanced: float
    pct_fabricated: float
    mean_confidence: float
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def classify(original_rgb: np.ndarray, final_rgb: np.ndarray, *,
             confidence: np.ndarray | None = None,
             fabricated_regions: dict[str, np.ndarray] | None = None,
             lum_enhance_thresh: int = 6, lum_fab_thresh: int = 28,
             sat_thresh: int = 12) -> tuple[np.ndarray, Authenticity]:
    """Return (class_map HxW uint8, Authenticity stats).

    - Luminance change small  -> ENHANCED (real signal, cleaned)
    - Luminance change large   -> FABRICATED (structure invented)
    - Any added chroma on a gray master -> FABRICATED (color inferred)
    - Explicit op regions (e.g. inpaint masks) -> FABRICATED
    """
    h, w = original_rgb.shape[:2]
    final = _resize_to(final_rgb, h, w)
    o_lab = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2LAB).astype(np.int16)
    f_lab = cv2.cvtColor(final, cv2.COLOR_RGB2LAB).astype(np.int16)

    dL = np.abs(f_lab[:, :, 0] - o_lab[:, :, 0])
    # chroma present in FINAL (original is ~neutral gray so any sat is added)
    sat = np.sqrt((f_lab[:, :, 1] - 128.0) ** 2 + (f_lab[:, :, 2] - 128.0) ** 2)

    cls = np.full((h, w), ORIGINAL, np.uint8)
    cls[dL >= lum_enhance_thresh] = ENHANCED
    cls[sat >= sat_thresh] = FABRICATED           # color is inferred
    cls[dL >= lum_fab_thresh] = FABRICATED         # structure changed
    if fabricated_regions:
        for m in fabricated_regions.values():
            cls[_resize_to(m, h, w) > 127] = FABRICATED

    total = h * w
    pct = lambda v: round(100.0 * float(np.count_nonzero(cls == v)) / total, 1)
    notes: list[str] = []
    if (sat >= sat_thresh).mean() > 0.5:
        notes.append("All color is AI-inferred; original is grayscale.")
    if fabricated_regions:
        notes.append(f"{len(fabricated_regions)} region(s) reconstructed (damage repair).")
    mean_conf = float(confidence.mean()) if confidence is not None else 1.0
    if confidence is not None and mean_conf < 0.8:
        notes.append("Low colorizer agreement in places — flagged as a guess.")

    return cls, Authenticity(pct(ORIGINAL), pct(ENHANCED), pct(FABRICATED),
                             round(mean_conf, 3), notes)


# ------------------------------------------------------------- rendering
def render_overlay(base_rgb: np.ndarray, class_map: np.ndarray, alpha: float = 0.55) -> bytes:
    """Color-coded authenticity overlay atop a desaturated base."""
    h, w = class_map.shape
    base = cv2.cvtColor(cv2.cvtColor(_resize_to(base_rgb, h, w), cv2.COLOR_RGB2GRAY),
                        cv2.COLOR_GRAY2RGB)
    overlay = np.zeros_like(base)
    for cid, rgb in CLASS_RGB.items():
        overlay[class_map == cid] = rgb
    out = (base * (1 - alpha) + overlay * alpha).astype(np.uint8)
    return to_png(out)


def render_confidence(base_rgb: np.ndarray, confidence: np.ndarray, alpha: float = 0.6) -> bytes:
    """Heatmap: low confidence (AI guessing) = vermilion, high = teal, over grayscale."""
    h, w = confidence.shape
    base = cv2.cvtColor(cv2.cvtColor(_resize_to(base_rgb, h, w), cv2.COLOR_RGB2GRAY),
                        cv2.COLOR_GRAY2RGB)
    teal = np.array(CLASS_RGB[ORIGINAL], np.float32)
    verm = np.array(CLASS_RGB[FABRICATED], np.float32)
    c = confidence[..., None]
    heat = (verm * (1 - c) + teal * c).astype(np.uint8)
    out = (base * (1 - alpha) + heat * alpha).astype(np.uint8)
    return to_png(out)
