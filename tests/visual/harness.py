"""Shared helpers for the visual (browser-reference) test suite.

Each test case is a standalone HTML file in ``cases/`` made of an optional metadata
comment, one ``<style>`` block and the markup to render::

    <!-- html2pic-test: {"max_diff_ratio": 0.03, "xfail": "why it differs"} -->
    <style>
      .box { width: 40px; height: 40px; background-color: red }
    </style>
    <div class="box"></div>

The same case is rendered by a real browser (see ``tools/generate_visual_references.py``)
and by html2pic, and the two images are compared pixel by pixel.

This module is imported both by the tests and by the reference generator, so it must not
import pytest or playwright.
"""
import base64
import hashlib
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

VISUAL_DIR = Path(__file__).resolve().parent
CASES_DIR = VISUAL_DIR / "cases"
REFERENCES_DIR = VISUAL_DIR / "references"
OUTPUT_DIR = VISUAL_DIR / "_output"
MANIFEST_PATH = REFERENCES_DIR / "manifest.json"

# Bump whenever PAGE_TEMPLATE (or anything else that changes how references are produced)
# changes, so every reference is flagged as stale and regenerated.
TEMPLATE_VERSION = 2

DEFAULT_OPTIONS: Dict[str, Any] = {
    # A pixel counts as different when any premultiplied RGBA channel differs by more than this.
    "pixel_threshold": 48,
    # Fraction of pixels allowed to differ. Anti-aliasing of edges and glyphs differs slightly
    # between Skia-in-PicTex and Chromium, so text-heavy cases need a higher value.
    "max_diff_ratio": 0.01,
    # A pixel also matches if a reference pixel up to this many px away (in x or y) matches it.
    # Use 1 for text: glyphs are positioned with sub-pixel precision, which shifts their
    # anti-aliased edges slightly between engines. Keep 0 for shapes so layout stays exact.
    "shift_tolerance": 0,
    # Allowed difference (in px) between the rendered and reference image sizes.
    "size_tolerance": 0,
    # Pass the case's <style> blocks to html2pic inside the HTML (exercising its own <style>
    # handling) instead of through the `css` argument.
    "styles_in_html": False,
    # When set, the case documents a known divergence from the browser and is expected to fail.
    "xfail": None,
}

_META_RE = re.compile(r"<!--\s*html2pic-test:\s*(\{.*?\})\s*-->", re.DOTALL)
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)

# The reference page reproduces html2pic's rendering model:
#  * html2pic has no user-agent stylesheet: every element starts with margin/padding 0,
#    16px font size, normal weight and line-height 1.2, so the reset below mimics that.
#  * The document is wrapped in a flex column that shrinks to its content, which is exactly
#    what html2pic's synthetic root is (a PicTex Column cropped to its content box).
#  * The default font is the Inter build bundled with PicTex, embedded as a data URL so the
#    browser uses the very same font file.
#  * Optical sizing is disabled: Chromium sets the variable font's 'opsz' axis from the font
#    size (font-optical-sizing: auto), but PicTex does not set that axis yet, which makes all
#    text ~3% wider. The `gap_font_optical_sizing` case documents this divergence.
# Everything else (box-sizing, margin collapsing, ...) is left to the browser on purpose:
# those are the behaviours the suite is meant to verify.
PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<base href="{base_href}">
<style>
@font-face {{
  font-family: "Inter";
  src: url(data:font/ttf;base64,{font_b64}) format("truetype");
  font-weight: 100 900;
  font-style: normal;
}}
html, body {{ margin: 0; padding: 0; background: transparent; }}
* {{ margin: 0; padding: 0; font-size: inherit; font-weight: inherit; list-style: none; }}
#__html2pic_capture {{
  display: inline-flex;
  flex-direction: column;
  font-family: "Inter";
  font-size: 16px;
  font-weight: 400;
  line-height: 1.2;
  color: black;
  font-optical-sizing: none;
}}
</style>
<style>
{css}
</style>
</head>
<body><div id="__html2pic_capture">{html}</div></body>
</html>
"""


@dataclass
class VisualCase:
    name: str
    path: Path
    html: str
    css: str
    options: Dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def html2pic_input(self) -> Tuple[str, str]:
        """(html, css) to give html2pic for this case."""
        if self.options["styles_in_html"]:
            return self.source, ""
        return self.html, self.css

    @property
    def reference_path(self) -> Path:
        return REFERENCES_DIR / f"{self.name}.png"

    @property
    def source_hash(self) -> str:
        digest = hashlib.sha256()
        digest.update(f"template-v{TEMPLATE_VERSION}\n".encode())
        digest.update(self.path.read_bytes())
        return digest.hexdigest()

    def browser_page(self) -> str:
        return PAGE_TEMPLATE.format(
            base_href=CASES_DIR.as_uri() + "/",
            font_b64=_inter_font_b64(),
            css=self.css,
            html=self.html,
        )


def load_case(path: Path) -> VisualCase:
    source = path.read_text(encoding="utf-8")

    options = dict(DEFAULT_OPTIONS)
    meta = _META_RE.search(source)
    if meta:
        overrides = json.loads(meta.group(1))
        unknown = set(overrides) - set(DEFAULT_OPTIONS)
        if unknown:
            raise ValueError(f"{path.name}: unknown html2pic-test options {sorted(unknown)}")
        options.update(overrides)
        source = source[: meta.start()] + source[meta.end():]

    css = "\n".join(m.group(1) for m in _STYLE_RE.finditer(source))
    html = _STYLE_RE.sub("", source).strip()
    return VisualCase(name=path.stem, path=path, html=html, css=css, options=options, source=source.strip())


def load_cases():
    return [load_case(p) for p in sorted(CASES_DIR.glob("*.html"))]


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return {"cases": {}}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _inter_font_path() -> Path:
    return Path(str(resources.files("pictex") / "fonts" / "InterVariable.ttf"))


_FONT_CACHE: Optional[str] = None


def _inter_font_b64() -> str:
    global _FONT_CACHE
    if _FONT_CACHE is None:
        _FONT_CACHE = base64.b64encode(_inter_font_path().read_bytes()).decode("ascii")
    return _FONT_CACHE


def inter_font_sha256() -> str:
    return hashlib.sha256(_inter_font_path().read_bytes()).hexdigest()


# --------------------------------------------------------------------------- comparison


@dataclass
class Comparison:
    expected_size: Tuple[int, int]
    actual_size: Tuple[int, int]
    diff_ratio: float
    diff_mask: Optional[np.ndarray]

    def summary(self) -> str:
        if self.diff_mask is None:
            return f"size {self.actual_size[0]}x{self.actual_size[1]} != reference {self.expected_size[0]}x{self.expected_size[1]}"
        summary = f"{self.diff_ratio:.2%} of pixels differ"
        if self.expected_size != self.actual_size:
            summary += f" (size {self.actual_size[0]}x{self.actual_size[1]} vs reference {self.expected_size[0]}x{self.expected_size[1]})"
        return summary


def _premultiplied(rgba: np.ndarray) -> np.ndarray:
    rgba = rgba.astype(np.int32)
    alpha = rgba[..., 3:4]
    rgb = rgba[..., :3] * alpha // 255
    return np.concatenate([rgb, alpha], axis=-1)


def compare_images(expected: np.ndarray, actual: np.ndarray, options: Dict[str, Any]) -> Tuple[bool, Comparison]:
    """Compare two (h, w, 4) RGBA arrays. Returns (passed, details)."""
    eh, ew = expected.shape[:2]
    ah, aw = actual.shape[:2]
    tolerance = options["size_tolerance"]
    if abs(eh - ah) > tolerance or abs(ew - aw) > tolerance:
        return False, Comparison((ew, eh), (aw, ah), 1.0, None)

    # Compare the common area; any extra rows/columns allowed by size_tolerance count as different.
    h, w = max(eh, ah), max(ew, aw)
    exp = np.zeros((h, w, 4), dtype=np.uint8)
    act = np.zeros((h, w, 4), dtype=np.uint8)
    exp[:eh, :ew] = expected
    act[:ah, :aw] = actual

    mask = _mismatch_mask(_premultiplied(exp), _premultiplied(act), options["pixel_threshold"], options["shift_tolerance"])
    ratio = float(mask.mean()) if mask.size else 0.0
    return ratio <= options["max_diff_ratio"], Comparison((ew, eh), (aw, ah), ratio, mask)


def _mismatch_mask(expected: np.ndarray, actual: np.ndarray, threshold: int, shift: int) -> np.ndarray:
    """Pixels of `actual` that match no pixel of `expected` within `shift` px (Chebyshev distance)."""
    h, w = actual.shape[:2]
    mismatch = np.ones((h, w), dtype=bool)
    padded = np.pad(expected, ((shift, shift), (shift, shift), (0, 0)), mode="edge")
    for dy in range(-shift, shift + 1):
        for dx in range(-shift, shift + 1):
            window = padded[shift + dy:shift + dy + h, shift + dx:shift + dx + w]
            mismatch &= np.abs(window - actual).max(axis=-1) > threshold
    return mismatch


def diff_image(expected: np.ndarray, actual: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Greyscale composite of both images with differing pixels highlighted in magenta."""
    h, w = mask.shape
    canvas = np.full((h, w, 4), 255, dtype=np.uint8)
    for img in (expected, actual):
        ih, iw = img.shape[:2]
        grey = (img[..., :3].mean(axis=-1) * img[..., 3] / 255 + 255 * (1 - img[..., 3] / 255)).astype(np.uint8)
        region = canvas[:ih, :iw, :3]
        region[:] = np.minimum(region, (grey[..., None] * 0.5 + 127).astype(np.uint8))
    canvas[mask] = (255, 0, 255, 255)
    return canvas
