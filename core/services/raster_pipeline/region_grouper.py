"""
Region Grouper — Maps SVG paths to pixel regions via label image
================================================================
Equivalent to api_paihong a6_group_paths_by_region.py.

Given:
  - an SVG root element (ET.Element)
  - a label array and area array from region_labeler
  - the pixel image dimensions (for coordinate scaling)

Groups each <path> element into the region whose label it belongs to,
then builds one SVG tree per region.
"""

import xml.etree.ElementTree as ET
import numpy as np
from svgelements import Path

SVG_NS = "http://www.w3.org/2000/svg"

# Only paths falling inside regions with area > this threshold are considered
MIN_REGION_AREA = 10_000
# Number of sample points taken along each path to vote for a region label
K_SAMPLE_POINTS = 7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _viewbox_size(root: ET.Element) -> tuple[float | None, float | None]:
    """Return (width, height) in user units from viewBox or width/height attributes."""
    vb = root.get("viewBox")
    if vb:
        parts = vb.replace(",", " ").split()
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])

    def _num(s: str | None) -> float | None:
        if not s:
            return None
        return float("".join(c for c in s if c.isdigit() or c in ".-"))

    return _num(root.get("width")), _num(root.get("height"))


def _sample_points(d: str, k: int = K_SAMPLE_POINTS) -> list[tuple[float, float]]:
    """Return representative points for a path: bbox centre + k evenly-spaced points."""
    try:
        path = Path(d)
    except Exception:
        return []

    pts: list[tuple[float, float]] = []
    bb = path.bbox()
    if bb:
        pts.append(((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0))

    try:
        length = path.length()
    except Exception:
        length = 0

    if length and length > 0:
        for i in range(k):
            t = (i + 0.5) / k
            p = path.point(t)
            pts.append((p.x, p.y))

    return pts


def _label_at(labels: np.ndarray, x: float, y: float, sx: float, sy: float) -> int:
    """Return the region label at SVG coordinate (x, y)."""
    h, w = labels.shape
    xi = int(round(x * sx))
    yi = int(round(y * sy))
    if 0 <= xi < w and 0 <= yi < h:
        return int(labels[yi, xi])
    return 0


def _dominant_label(
    labels: np.ndarray,
    areas: np.ndarray,
    pts: list[tuple[float, float]],
    sx: float,
    sy: float,
) -> int:
    """Return the label that appears most often among the sample points."""
    votes: dict[int, int] = {}
    for x, y in pts:
        lbl = _label_at(labels, x, y, sx, sy)
        if lbl == 0:
            continue
        votes[lbl] = votes.get(lbl, 0) + 1

    if not votes:
        return 0
    return max(votes, key=lambda lbl: (votes[lbl], areas[lbl]))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def group_paths_by_region(
    root: ET.Element,
    labels: np.ndarray,
    areas: np.ndarray,
    img_h: int,
    img_w: int,
) -> tuple[list[ET.Element], list[list[str]]]:
    """
    Assign each <path> and <text> element in root to a pixel region and build one
    SVG <svg> element per region.

    Args:
        root    : Parsed SVG root element (already preprocessed)
        labels  : 2-D int64 label array from region_labeler (shape: img_h × img_w)
        areas   : Pixel area per label
        img_h   : Height of the label image in pixels
        img_w   : Width of the label image in pixels

    Returns:
        (out_svgs, out_texts)
    """
    vw, vh = _viewbox_size(root)
    sx = img_w / vw if vw else 1.0
    sy = img_h / vh if vh else 1.0

    # Paths inside <defs> are font glyphs → skip
    glyph_ids: set[int] = set()
    for defs in root.iter(f"{{{SVG_NS}}}defs"):
        for p in defs.iter(f"{{{SVG_NS}}}path"):
            glyph_ids.add(id(p))

    # Map each qualifying path/text to a region label
    region_paths: dict[int, list[ET.Element]] = {}
    region_texts: dict[int, list[str]] = {}
    
    # Process paths
    for el in root.iter(f"{{{SVG_NS}}}path"):
        if id(el) in glyph_ids:
            continue
        d = el.get("d")
        if not d:
            continue
        try:
            pts = _sample_points(d)
        except Exception:
            continue

        lbl = _dominant_label(labels, areas, pts, sx, sy)
        if lbl == 0 or areas[lbl] <= MIN_REGION_AREA:
            continue
        region_paths.setdefault(lbl, []).append(el)
        
    # Process texts
    for el in root.iter(f"{{{SVG_NS}}}text"):
        x = float(el.get("x") or 0)
        y = float(el.get("y") or 0)
        
        # Apply baked transforms to find the true pixel location
        t_attr = el.get("transform")
        if t_attr:
            try:
                from svgelements import Matrix, Point
                pt = Point(x, y) * Matrix(t_attr)
                x, y = pt.x, pt.y
            except Exception:
                pass
                
        lbl = _dominant_label(labels, areas, [(x, y)], sx, sy)
        if lbl == 0 or areas[lbl] <= MIN_REGION_AREA:
            continue
            
        txt_val = el.text or ""
        if txt_val.strip():
            region_texts.setdefault(lbl, []).append(txt_val.strip())

    if not region_paths:
        return [], []

    # Build one SVG element per region (largest area first)
    ET.register_namespace("", SVG_NS)
    width = root.get("width")
    height = root.get("height")
    viewbox = root.get("viewBox")

    out_svgs: list[ET.Element] = []
    out_texts: list[list[str]] = []
    
    for lbl in sorted(region_paths, key=lambda l: -areas[l]):
        new_svg = ET.Element(f"{{{SVG_NS}}}svg")
        if width:
            new_svg.set("width", width)
        if height:
            new_svg.set("height", height)
        if viewbox:
            new_svg.set("viewBox", viewbox)
        for el in region_paths[lbl]:
            new_svg.append(el)
        out_svgs.append(new_svg)
        out_texts.append(region_texts.get(lbl, []))

    return out_svgs, out_texts
