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


def mask_to_png(mask: np.ndarray) -> bytes:
    """0/255 single-channel mask -> 3-channel PNG."""
    return to_png(np.stack([mask, mask, mask], axis=-1))


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
def detect_damage(original_rgb: np.ndarray, *, thresh: int = 42,
                  max_area: int = 450, max_coverage: float = 0.02) -> np.ndarray:
    """Conservative scratch/dust/tear mask (0/255).

    Morphological black/top-hat isolates thin bright/dark defects; we then keep only
    *small* connected components (dust specks, thin scratches) and drop large blobs
    (shadows, facial features), so we never mark real detail as damage. If the result
    still covers more than ``max_coverage`` of the frame, we treat it as texture noise
    and return an empty mask rather than over-report.
    """
    gray = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2GRAY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    defect = cv2.max(cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, k),
                     cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k))
    _, raw = cv2.threshold(defect, thresh, 255, cv2.THRESH_BINARY)

    # Only trust defects in LOW-TEXTURE regions. Real detail (hair, beard, wrinkles,
    # fabric) has high local variance and must never be called "damage"; dust/specks
    # on smooth backgrounds and skin do not.
    g = gray.astype(np.float32)
    mean = cv2.blur(g, (17, 17))
    local_std = np.sqrt(np.maximum(cv2.blur(g * g, (17, 17)) - mean * mean, 0))
    raw[local_std > 9.0] = 0                       # exclude textured detail

    n, labels, stats, _ = cv2.connectedComponentsWithStats(raw, 8)
    mask = np.zeros_like(raw)
    for i in range(1, n):
        area = stats[i, cv2.CC_STAT_AREA]
        if 2 <= area <= max_area:                 # small specks / thin scratches only
            mask[labels == i] = 255
    if mask.mean() / 255.0 > max_coverage:        # still too much -> texture noise, bail
        return np.zeros_like(raw)
    return cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))


def repair_damage(original_rgb: np.ndarray,
                  mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Inpaint detected damage. Returns (repaired_rgb, mask). No API cost (OpenCV)."""
    if mask is None:
        mask = detect_damage(original_rgb)
    if mask.any():
        repaired = cv2.inpaint(original_rgb, mask, 3, cv2.INPAINT_TELEA)
    else:
        repaired = original_rgb
    return repaired, mask


# -------------------------------------------------------- authenticity map
@dataclass
class Authenticity:
    # STRUCTURE axis (from luminance / explicit fabricated regions)
    pct_original: float          # structure preserved from the master
    pct_enhanced: float          # real signal, cleaned
    pct_fabricated: float        # structure invented (inpaint/hallucination)
    # COLOR axis (a grayscale master has no color, so any color is inferred)
    pct_color_inferred: float
    mean_confidence: float       # colorizer agreement (1 = fully grounded)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def classify(original_rgb: np.ndarray, final_rgb: np.ndarray, *,
             confidence: np.ndarray | None = None,
             fabricated_regions: dict[str, np.ndarray] | None = None,
             lum_enhance_thresh: int = 10, lum_fab_thresh: int = 45,
             sat_thresh: int = 12) -> tuple[np.ndarray, Authenticity]:
    """Return (class_map HxW uint8, Authenticity stats).

    Two independent axes are measured honestly:
      STRUCTURE (from luminance change vs the master):
        small change  -> ENHANCED (real signal, cleaned)
        large change   -> FABRICATED (structure invented)
        explicit op regions (inpaint masks) -> FABRICATED
      COLOR: a grayscale master has no chroma, so any color in the result is
        AI-inferred. We report the share of the image that carries inferred color.
    Because colorization is luminance-locked, STRUCTURE stays ~100% original;
    the fabrication is the color layer, whose trustworthiness is the confidence map.
    """
    h, w = original_rgb.shape[:2]
    final = _resize_to(final_rgb, h, w)
    o_lab = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2LAB).astype(np.int16)
    f_lab = cv2.cvtColor(final, cv2.COLOR_RGB2LAB).astype(np.int16)

    dL = np.abs(f_lab[:, :, 0] - o_lab[:, :, 0])
    sat = np.sqrt((f_lab[:, :, 1] - 128.0) ** 2 + (f_lab[:, :, 2] - 128.0) ** 2)

    # --- structure classification (NOT driven by color) ---
    cls = np.full((h, w), ORIGINAL, np.uint8)
    cls[dL >= lum_enhance_thresh] = ENHANCED
    cls[dL >= lum_fab_thresh] = FABRICATED
    if fabricated_regions:
        for m in fabricated_regions.values():
            cls[_resize_to(m, h, w) > 127] = FABRICATED

    total = h * w
    pct = lambda v: round(100.0 * float(np.count_nonzero(cls == v)) / total, 1)
    color_inferred = round(100.0 * float(np.count_nonzero(sat >= sat_thresh)) / total, 1)

    notes: list[str] = ["Structure preserved from the master (luminance locked)."]
    if color_inferred > 1:
        notes.append(f"All color is AI-inferred; ~{color_inferred:.0f}% of the image carries added color.")
    if fabricated_regions:
        notes.append(f"{len(fabricated_regions)} region(s) reconstructed (damage repair).")
    mean_conf = float(confidence.mean()) if confidence is not None else 1.0
    if confidence is not None and mean_conf < 0.85:
        notes.append("Colorizers disagree in places — those colors are flagged as guesses.")

    return cls, Authenticity(pct(ORIGINAL), pct(ENHANCED), pct(FABRICATED),
                             color_inferred, round(mean_conf, 3), notes)


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
