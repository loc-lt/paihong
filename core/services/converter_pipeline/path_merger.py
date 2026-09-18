import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

from svgpathtools import CubicBezier, Line, Path, QuadraticBezier, parse_path

from core.services.converter_pipeline.math_ops import (
    apply_affine, 
    full_matrix, 
    Matrix
)

PathItem = Tuple[int, Path, Dict[str, str]]

KEEP_ATTRS = (
    "style", "fill", "stroke", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray",
    "fill-rule", "opacity", "fill-opacity", "stroke-opacity",
)
SVG_NS = "http://www.w3.org/2000/svg"

def transform_path(path: Path, matrix: Matrix) -> Path:
    """Apply a matrix to every point of a path (result is in absolute space)."""
    result = Path()
    for segment in path:
        try:
            points = [apply_affine(p, matrix) for p in segment.bpoints()]
        except AttributeError:
            for cubic in segment.as_cubic_curves(4):
                result.append(CubicBezier(*[apply_affine(p, matrix) for p in cubic.bpoints()]))
            continue

        if len(points) == 2:
            result.append(Line(*points))
        elif len(points) == 3:
            result.append(QuadraticBezier(*points))
        elif len(points) == 4:
            result.append(CubicBezier(*points))
    return result

def keep_attrib(element: ET.Element) -> Dict[str, str]:
    """Return the reusable presentation attributes of the original path."""
    return {k: element.get(k) for k in KEEP_ATTRS if element.get(k) is not None}

def is_duplicate(start: complex, end: complex, seen: List[Tuple[complex, complex]], tol: float) -> bool:
    """True if (start, end) matches a kept path, in either direction."""
    for prev_start, prev_end in seen:
        same = abs(start - prev_start) <= tol and abs(end - prev_end) <= tol
        reversed_ = abs(start - prev_end) <= tol and abs(end - prev_start) <= tol
        if same or reversed_:
            return True
    return False

def collect_line_paths(root: ET.Element, tol: float) -> Tuple[List[PathItem], List[ET.Element]]:
    """Split the SVG paths into open line paths to merge and elements to remove."""
    parents = {child: parent for parent in root.iter() for child in parent}
    paths_data = []
    for i, el in enumerate(root.iter()):
        if el.tag.split("}")[-1] == "path":
            paths_data.append({"index": i, "element": el, "d": el.get("d")})

    line_items = []
    line_elems = []
    seen = []

    for p in paths_data:
        if not p["d"]:
            continue

        matrix = full_matrix(p["element"], parents)
        try:
            parsed = parse_path(p["d"])
        except Exception:
            continue
        
        abs_path = transform_path(parsed, matrix)
        if len(abs_path) == 0:
            continue
            
        start, end = abs_path.start, abs_path.end

        if abs(start - end) <= tol or "z" in p["d"].lower():
            continue

        line_elems.append(p["element"])
        if is_duplicate(start, end, seen, tol):
            continue
            
        seen.append((start, end))
        line_items.append((p["index"], abs_path, keep_attrib(p["element"])))

    return line_items, line_elems

def merge_once(chains: List[Tuple[List[int], Path, Dict[str, str]]], tol: float) -> List[Tuple[List[int], Path, Dict[str, str]]]:
    """Run one merging pass, greedily joining chains that share an endpoint."""
    todo = [c for c in chains if len(c[1]) > 0]
    result = []

    while todo:
        members, chain, attrib = todo.pop(0)
        members = list(members)

        joined = True
        while joined:
            joined = False
            for k, (other_members, other, _) in enumerate(todo):
                end, start = chain.end, chain.start
                o_end, o_start = other.end, other.start

                if abs(end - o_start) <= tol:
                    chain = Path(*chain, *other)
                elif abs(end - o_end) <= tol:
                    chain = Path(*chain, *other.reversed())
                elif abs(start - o_end) <= tol:
                    chain = Path(*other, *chain)
                elif abs(start - o_start) <= tol:
                    chain = Path(*other.reversed(), *chain)
                else:
                    continue

                members.extend(other_members)
                todo.pop(k)
                joined = True
                break

        for prev, nxt in zip(chain[:-1], chain[1:]):
            nxt.start = prev.end
        if 0 < abs(chain.end - chain.start) <= tol:
            chain[0].start = chain.end

        result.append([members, chain, attrib])
    return result

def merge(items: List[PathItem], tol: float) -> List[Tuple[List[int], Path, Dict[str, str]]]:
    """Merge repeatedly until no further pair can be joined."""
    work = [[[idx], path, attrib] for idx, path, attrib in items]
    while True:
        merged = merge_once(work, tol)
        if len(merged) == len(work):
            return merged
        work = merged

def endpoints_touch(pa: Path, pb: Path, tol: float) -> bool:
    """True if any endpoint of pa is within tol of any endpoint of pb."""
    return any(abs(x - y) <= tol for x in (pa.start, pa.end) for y in (pb.start, pb.end))

def group_components(items: List[PathItem], tol: float) -> List[List[PathItem]]:
    """Group items into connected components by shared endpoints (union-find)."""
    n = len(items)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    paths = [item[1] for item in items]
    for i in range(n):
        for j in range(i + 1, n):
            if endpoints_touch(paths[i], paths[j], tol):
                union(i, j)

    components = {}
    for i in range(n):
        components.setdefault(find(i), []).append(items[i])
    return list(components.values())

def build_groups(items: List[PathItem], tol: float) -> List[Tuple[Path, Dict[str, str]]]:
    """Group paths, then merge each group into one combined <path>."""
    components = group_components(items, tol)
    groups = []
    for component in components:
        chains = merge(component, tol)
        segments = []
        for _, chain, _ in chains:
            segments.extend(list(chain))
        if segments:
            combined = Path(*segments)
            attrib = component[0][2]
            groups.append((combined, attrib))
    return groups

def clean_and_merge_lines(root: ET.Element, tol: float) -> None:
    """Removes open line paths and appends merged paths in-place."""
    line_items, line_elems = collect_line_paths(root, tol)
    groups = build_groups(line_items, tol)
    
    parents = {child: parent for parent in root.iter() for child in parent}
    for el in line_elems:
        parents[el].remove(el)

    for combined, attrib in groups:
        el = ET.SubElement(root, f"{{{SVG_NS}}}path")
        for k, v in attrib.items():
            el.set(k, v)
        el.set("d", combined.d())
