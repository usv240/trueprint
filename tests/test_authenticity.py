"""Unit tests for the authenticity engine — pure CV, no API/credentials needed."""
import numpy as np
import cv2
from backend.app import authenticity as A

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _gray(h=80, w=64):
    g = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    return cv2.cvtColor(g, cv2.COLOR_GRAY2RGB)


def _colormap(rgb, cmap):
    return cv2.cvtColor(cv2.applyColorMap(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), cmap), cv2.COLOR_BGR2RGB)


def _muted_color(rgb):
    """A realistic, muted colorization (not a pathological max-saturation colormap)."""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.int16)
    lab[:, :, 1] = np.clip(lab[:, :, 1] + 14, 0, 255)   # slight warm/green tint
    lab[:, :, 2] = np.clip(lab[:, :, 2] + 9, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)


def test_colorize_recombine_preserves_luminance():
    orig = _gray()
    out = A.colorize_recombine(orig, _muted_color(orig))
    lo = cv2.cvtColor(orig, cv2.COLOR_RGB2LAB)[:, :, 0].astype(int)
    lout = cv2.cvtColor(out, cv2.COLOR_RGB2LAB)[:, :, 0].astype(int)
    assert np.abs(lo - lout).mean() < 6, "luminance (structure) must be preserved for realistic color"


def test_confidence_agreement_vs_disagreement():
    orig = _gray()
    a = _colormap(orig, cv2.COLORMAP_OCEAN)
    _, m_same = A.color_confidence(orig, [a, a])
    assert m_same > 0.99, "identical samples must yield ~full confidence"
    b = _colormap(orig, cv2.COLORMAP_HOT)
    _, m_diff = A.color_confidence(orig, [a, b])
    assert m_diff < m_same, "disagreeing samples must lower confidence"


def test_classify_two_axes():
    orig = _gray()
    final = A.colorize_recombine(orig, _colormap(orig, cv2.COLORMAP_JET))
    cls, stats = A.classify(orig, final)
    assert 0 <= stats.pct_original <= 100
    assert stats.pct_color_inferred > 50, "colormap adds lots of color"
    assert stats.pct_fabricated < 5, "structure is luminance-locked -> ~0 fabricated"
    assert stats.notes and "Structure preserved" in stats.notes[0]


def test_detect_damage_is_conservative_on_clean_image():
    mask = A.detect_damage(_gray(160, 160))
    assert (mask > 0).mean() < 0.02, "must not mark a clean gradient as damage"


def test_renderers_return_png():
    orig = _gray()
    cls, _ = A.classify(orig, orig)
    conf = np.ones(orig.shape[:2], dtype="float32")
    assert A.render_overlay(orig, cls)[:8] == PNG_MAGIC
    assert A.render_confidence(orig, conf)[:8] == PNG_MAGIC
    assert A.mask_to_png(A.detect_damage(orig))[:8] == PNG_MAGIC
