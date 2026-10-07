"""
SVG Pre-processor for Raster Pipeline
======================================
Combines api_paihong steps a1.5, a2, a3, a3.5 into a single in-memory pass
that operates on an SVG *string* and returns a cleaned SVG *string*.

Steps:
  1. expand_use_elements  — flatten <use> → <path>
  2. bake_transforms      — bake accumulated transforms into 'd'
  3. normalize_strokes    — strip inline styles, set uniform black stroke
  4. remove_big_quads     — remove background rectangle frames (Shoelace Area)
"""

import io
import xml.etree.ElementTree as ET
from svgelements import Path, Matrix

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

# Raster pipeline uses uniform strokes so pixel regions are cleanly separated
STROKE_COLOR = "#000000"
STROKE_WIDTH = "1"

# Any straight-sided quad with area above this threshold is considered a background frame
BIG_QUAD_AREA_MAX = 100_000


# ---------------------------------------------------------------------------
# Namespace helpers (same pattern as api_paihong)
# ---------------------------------------------------------------------------

def _register_namespaces(svg_string: str) -> None:
    """Pre-register known namespace prefixes so ET doesn't rename them."""
    known = {
        XLINK_NS: "xlink",
        "http://www.inkscape.org/namespaces/inkscape": "inkscape",
    }
    for _, (prefix, uri) in ET.iterparse(io.StringIO(svg_string), events=["start-ns"]):
        if prefix.startswith("ns") and prefix[2:].isdigit():
            if uri in known:
                ET.register_namespace(known[uri], uri)
            continue
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass


def _build_parent_map(root: ET.Element) -> dict:
    return {child: parent for parent in root.iter() for child in parent}


def _get_href(el: ET.Element) -> str | None:
    return el.get("href") or el.get(f"{{{XLINK_NS}}}href")


# ---------------------------------------------------------------------------
# Step 1 — Expand <use> → <path>
# ---------------------------------------------------------------------------

def _expand_use_elements(root: ET.Element) -> None:
    id_map = {el.get("id"): el for el in root.iter() if el.get("id")}
    parent_map = _build_parent_map(root)

    for use in list(root.iter(f"{{{SVG_NS}}}use")):
        href = _get_href(use)
        if not href or not href.startswith("#"):
            continue
        ref = id_map.get(href[1:])
        if ref is None or not ref.get("d"):
            continue

        M = Matrix()
        if use.get("transform"):
            M = Matrix(use.get("transform"))
        x = float(use.get("x") or 0)
        y = float(use.get("y") or 0)
        if x or y:
            M = M * Matrix.translate(x, y)

        try:
            d = ref.get("d")
            baked = (Path(d) * M).d() if not M.is_identity() else Path(d).d()
        except Exception:
            continue

        new_path = ET.Element(f"{{{SVG_NS}}}path")
        for k, v in use.attrib.items():
            if k.split("}")[-1] not in ("href", "x", "y", "transform"):
                new_path.set(k, v)
        new_path.set("d", baked)

        parent = parent_map.get(use)
        if parent is not None:
            idx = list(parent).index(use)
            parent.remove(use)
            parent.insert(idx, new_path)


# ---------------------------------------------------------------------------
# Step 2 — Bake accumulated transforms into 'd'
# ---------------------------------------------------------------------------

def _bake_transforms(root: ET.Element) -> None:
    parent_map = _build_parent_map(root)

    for el in list(root.iter(f"{{{SVG_NS}}}path")):
        d = el.get("d")
        if not d:
            continue
        chain = []
        node = el
        while node is not None:
            t = node.get("transform")
            if t:
                chain.append(t)
            node = parent_map.get(node)
        M = Matrix()
        for t in reversed(chain):
            M = M * Matrix(t)
        if M.is_identity():
            continue
        try:
            el.set("d", (Path(d) * M).d())
            if el.get("transform"):
                del el.attrib["transform"]
        except Exception:
            continue

    # 1.5 Bake transforms for <text> by preserving it explicitly
    for el in list(root.iter(f"{{{SVG_NS}}}text")):
        chain = []
        node = el
        while node is not None:
            t = node.get("transform")
            if t:
                chain.append(t)
            node = parent_map.get(node)
        M = Matrix()
        for t in reversed(chain):
            M = M * Matrix(t)
        if not M.is_identity():
            el.set("transform", f"matrix({M.a}, {M.b}, {M.c}, {M.d}, {M.e}, {M.f})")

    for img in list(root.iter(f"{{{SVG_NS}}}image")):
        p = parent_map.get(img)
        if p is not None:
            p.remove(img)

    for g in root.iter(f"{{{SVG_NS}}}g"):
        if g.get("transform"):
            del g.attrib["transform"]


# ---------------------------------------------------------------------------
# Step 3 — Normalize strokes (uniform black, no fill, no inline style)
# ---------------------------------------------------------------------------

def _normalize_strokes(root: ET.Element) -> None:
    glyph_ids: set[int] = set()
    for defs in root.iter(f"{{{SVG_NS}}}defs"):
        for p in defs.iter(f"{{{SVG_NS}}}path"):
            glyph_ids.add(id(p))

    for el in root.iter(f"{{{SVG_NS}}}path"):
        if id(el) in glyph_ids or not el.get("d"):
            continue
        if el.get("style") is not None:
            del el.attrib["style"]
        el.set("fill", "none")
        el.set("stroke", STROKE_COLOR)
        el.set("stroke-width", STROKE_WIDTH)


# ---------------------------------------------------------------------------
# Step 4 — Remove large background quadrilaterals (Shoelace Area)
# ---------------------------------------------------------------------------

def _shoelace_area(pts: list[tuple]) -> float:
    n = len(pts)
    s = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def _is_big_quad(d: str) -> bool:
    """Return True if the path is a straight-sided quadrilateral with large area."""
    from svgelements import Path as SvgPath, Move, Line, Close
    try:
        path = SvgPath(d)
    except Exception:
        return False

    pts = []
    for seg in path:
        if isinstance(seg, Move):
            pts.append((seg.end.x, seg.end.y))
        elif isinstance(seg, (Line, Close)):
            pts.append((seg.end.x, seg.end.y))
        else:
            return False  # Bezier/arc present → not a pure polygon

    # Deduplicate consecutive identical points and close-point
    def _dedup(points):
        cleaned = []
        for p in points:
            if not cleaned or abs(cleaned[-1][0] - p[0]) > 1e-6 or abs(cleaned[-1][1] - p[1]) > 1e-6:
                cleaned.append(p)
        while len(cleaned) >= 2 and abs(cleaned[0][0] - cleaned[-1][0]) < 1e-6 and abs(cleaned[0][1] - cleaned[-1][1]) < 1e-6:
            cleaned.pop()
        return cleaned

    pts = _dedup(pts)
    if len(pts) != 4:
        return False
    return _shoelace_area(pts) > BIG_QUAD_AREA_MAX


def _remove_big_quads(root: ET.Element) -> None:
    parent_map = _build_parent_map(root)

    glyph_ids: set[int] = set()
    for defs in root.iter(f"{{{SVG_NS}}}defs"):
        for p in defs.iter(f"{{{SVG_NS}}}path"):
            glyph_ids.add(id(p))

    for el in list(root.iter(f"{{{SVG_NS}}}path")):
        if id(el) in glyph_ids:
            continue
        d = el.get("d")
        if d and _is_big_quad(d):
            parent = parent_map.get(el)
            if parent is not None:
                parent.remove(el)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def preprocess_svg(svg_string: str) -> str:
    """
    Run all 4 pre-processing steps on an SVG string and return the cleaned SVG string.

    Steps applied:
      1. Expand <use> elements into <path>
      2. Bake accumulated transform matrices into 'd' attributes
      3. Normalize strokes (uniform black, 1px, no fill, no inline style)
      4. Remove large background quadrilateral frames
    """
    _register_namespaces(svg_string)
    ET.register_namespace("", SVG_NS)

    root = ET.fromstring(svg_string)

    _expand_use_elements(root)
    _bake_transforms(root)
    _normalize_strokes(root)
    _remove_big_quads(root)

    return ET.tostring(root, encoding="unicode")
