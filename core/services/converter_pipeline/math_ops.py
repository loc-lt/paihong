import math
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from svgpathtools import parse_path

Matrix = Tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

def compose(m1: Matrix, m2: Matrix) -> Matrix:
    """Return the matrix equivalent to applying m2 first, then m1."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )

def parse_transform(transform: Optional[str]) -> Matrix:
    """Parse an SVG transform string (possibly chained) into a matrix."""
    matrix = IDENTITY
    if not transform:
        return matrix

    pattern = r"(matrix|translate|scale|rotate)\s*\(([^)]*)\)"
    for name, raw_args in re.findall(pattern, transform):
        values = [float(x) for x in re.split(r"[,\s]+", raw_args.strip()) if x]

        if name == "matrix" and len(values) == 6:
            step: Matrix = tuple(values)
        elif name == "translate":
            tx = values[0]
            ty = values[1] if len(values) > 1 else 0.0
            step = (1.0, 0.0, 0.0, 1.0, tx, ty)
        elif name == "scale":
            sx = values[0]
            sy = values[1] if len(values) > 1 else sx
            step = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "rotate":
            angle = math.radians(values[0])
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            step = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
            if len(values) == 3:
                cx, cy = values[1], values[2]
                step = compose(
                    compose((1.0, 0.0, 0.0, 1.0, cx, cy), step),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
        else:
            continue
        matrix = compose(matrix, step)
    return matrix

def apply_affine(point: complex, matrix: Matrix) -> complex:
    """Apply an affine matrix to a point expressed as a complex number."""
    a, b, c, d, e, f = matrix
    return complex(
        a * point.real + c * point.imag + e,
        b * point.real + d * point.imag + f,
    )

def apply_affine_pt(point: Tuple[float, float], matrix: Matrix) -> Tuple[float, float]:
    """Apply an affine matrix to a point expressed as a coordinate tuple."""
    a, b, c, d, e, f = matrix
    return (
        a * point[0] + c * point[1] + e,
        b * point[0] + d * point[1] + f,
    )

def full_matrix(element: ET.Element, parents: Dict[ET.Element, ET.Element]) -> Matrix:
    """Combine the transforms of the element and all of its ancestors."""
    lineage = []
    current = element
    while current is not None:
        lineage.append(current)
        current = parents.get(current)

    matrix = IDENTITY
    for node in reversed(lineage):
        matrix = compose(matrix, parse_transform(node.get("transform")))
    return matrix

def matrix_str(m: Matrix) -> str:
    """Convert a matrix tuple to SVG matrix string."""
    return "matrix({},{},{},{},{},{})".format(*m)

def points_from_d(d: str) -> List[complex]:
    """Extract points from path `d` string."""
    try:
        path = parse_path(d)
        pts = []
        for segment in path:
            if not pts:
                pts.append(segment.start)
            pts.append(segment.end)
        return pts
    except Exception:
        return []

def split_subpaths(d: str) -> List[str]:
    """Split the `d` string into subpaths by M/m commands."""
    starts = [m.start() for m in re.finditer(r"[Mm]", d)]
    if not starts:
        return [d]
    starts.append(len(d))
    subs = []
    for a, b in zip(starts[:-1], starts[1:]):
        seg = d[a:b].strip()
        if seg:
            subs.append(seg)
    return subs

def polygon_area(pts: List[Tuple[float, float]]) -> float:
    """Polygon area (shoelace algorithm), always non-negative."""
    n = len(pts)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0

def point_seg_dist(p: complex, a: complex, b: complex) -> float:
    """Distance from point p to segment a-b (p, a, b are complex numbers)."""
    ab = b - a
    L2 = ab.real**2 + ab.imag**2
    if L2 == 0:
        return abs(p - a)
    t = ((p.real - a.real) * ab.real + (p.imag - a.imag) * ab.imag) / L2
    t = max(0.0, min(1.0, t))
    proj = a + t * ab
    return abs(p - proj)

def closure_dangling(subs_pts: List[List[complex]], tol: float) -> List[complex]:
    """Find the OPEN endpoints of a path (made of multiple subpaths)."""
    segs = []
    for si, pts in enumerate(subs_pts):
        for k in range(len(pts) - 1):
            segs.append((si, k, pts[k], pts[k + 1]))

    def connected(pt: complex, si: int, incident: set) -> bool:
        """Does pt touch any segment (except its own adjacent ones)?"""
        for sj, k, a, b in segs:
            if sj == si and k in incident:
                continue
            if point_seg_dist(pt, a, b) <= tol:
                return True
        return False

    dangling = []
    for si, pts in enumerate(subs_pts):
        if len(pts) < 2:
            continue
        last = len(pts) - 2
        s = pts[0]
        e = pts[-1]
        if not connected(s, si, {0}):
            dangling.append(s)
        if not connected(e, si, {last}):
            dangling.append(e)
    return dangling
