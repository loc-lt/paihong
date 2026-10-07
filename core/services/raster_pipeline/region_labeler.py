"""
Region Labeler — PNG bytes → labelled PNG bytes (in-memory)
============================================================
Equivalent to api_paihong a5_fill_enclosed.py + a5_label_regions.py.

Steps:
  1. fill_enclosed  — flood-fill white holes inside black strokes
  2. label_regions  — assign each connected black region a unique color,
                      merge small regions into nearest large region
"""

import io
import numpy as np
from PIL import Image
from scipy import ndimage

# Pixels <= THRESHOLD are treated as black (part of the drawing lines)
THRESHOLD = 254
# 8-neighbor connectivity
CONNECTIVITY = 2
# Regions with pixel area below this are "small" and will be merged
BIG_AREA_MIN = 10_000
WHITE = (255, 255, 255)


# ---------------------------------------------------------------------------
# Step 1 — Fill enclosed white areas
# ---------------------------------------------------------------------------

def _fill_enclosed(gray: np.ndarray) -> np.ndarray:
    """
    Binary flood-fill: white areas that are completely enclosed by black
    strokes become black. This ensures closed-contour regions are solid.
    """
    black = gray <= THRESHOLD
    filled = ndimage.binary_fill_holes(black)
    # Return a uint8 grayscale: 0 = black, 255 = white
    return np.where(filled, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Step 2 — Label regions by unique color
# ---------------------------------------------------------------------------

def _color_table(n: int, seed: int = 0) -> np.ndarray:
    """Generate n+1 distinct colors (index 0 = white background)."""
    rng = np.random.default_rng(seed)
    colors = np.zeros((n + 1, 3), dtype=np.uint8)
    colors[0] = WHITE
    if n > 0:
        colors[1:] = rng.integers(30, 220, size=(n, 3), dtype=np.uint8)
    return colors


def _label_regions(gray_filled: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Connected-component labelling on the filled image.
    Small regions are merged into the nearest large region.

    Returns:
        labels      — 2-D int64 array (0 = background)
        areas       — 1-D int64 array, areas[lbl] = pixel count
        n_regions   — total number of distinct non-background labels
    """
    black = gray_filled <= THRESHOLD
    structure = ndimage.generate_binary_structure(2, CONNECTIVITY)
    labels, n = ndimage.label(black, structure=structure)

    counts = np.bincount(labels.ravel(), minlength=n + 1)
    areas = counts.astype(np.int64)

    big = [lbl for lbl in range(1, n + 1) if areas[lbl] > BIG_AREA_MIN]
    small = [lbl for lbl in range(1, n + 1) if 0 < areas[lbl] <= BIG_AREA_MIN]

    remap = np.arange(n + 1)
    if big and small:
        big_mask = np.isin(labels, big)
        _, (iy, ix) = ndimage.distance_transform_edt(~big_mask, return_indices=True)
        nearest_big_label = labels[iy, ix]
        for lbl in small:
            near_vals = nearest_big_label[labels == lbl]
            near_vals = near_vals[near_vals > 0]
            if near_vals.size:
                remap[lbl] = int(np.bincount(near_vals).argmax())

    labels = remap[labels]
    return labels, areas, n


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def label_png_bytes(png_bytes: bytes) -> tuple[bytes, np.ndarray, np.ndarray, int]:
    """
    Run fill_enclosed + label_regions on a PNG image provided as raw bytes.

    Args:
        png_bytes: Raw PNG bytes (as produced by raster_renderer).

    Returns:
        label_png_bytes — PNG bytes where each region has a unique color
        labels          — 2-D int64 label array (0 = background)
        areas           — pixel area per label
        n_regions       — number of distinct non-background labels found
    """
    gray = np.asarray(Image.open(io.BytesIO(png_bytes)).convert("L"))
    gray_filled = _fill_enclosed(gray)
    labels, areas, n = _label_regions(gray_filled)

    colors = _color_table(n)
    rgb_arr = colors[labels]
    label_img = Image.fromarray(rgb_arr, mode="RGB")

    buf = io.BytesIO()
    label_img.save(buf, format="PNG")
    return buf.getvalue(), labels, areas, n
