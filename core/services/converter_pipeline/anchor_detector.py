import xml.etree.ElementTree as ET
from typing import List

from shapely.geometry import Polygon
from shapely.ops import unary_union

from core.services.converter_pipeline.math_ops import (
    closure_dangling, 
    full_matrix, 
    points_from_d, 
    polygon_area, 
    split_subpaths
)

from core.services.converter_pipeline.constants import AREA_MIN, JOIN_TOL, MAX_BACKGROUND_RATIO

def build_polygons_from_paths(root: ET.Element, tol: float) -> List[Polygon]:
    """
    Extract geometric polygons from closed paths in the SVG document.
    Filters paths that are open, self-intersecting, or have tiny area.
    """
    par = {c: p for p in root.iter() for c in p}
    paths = [e for e in root.iter() if e.tag.split("}")[-1] == "path"]
    
    valid_polygons = []
    for el in paths:
        d = el.get("d")
        if not d:
            continue
            
        subs_pts = []
        for sp in split_subpaths(d):
            pts = []
            for p in points_from_d(sp):
                if not pts or p != pts[-1]:
                    pts.append(p)
            subs_pts.append(pts)

        n_pts = sum(len(pts) for pts in subs_pts)
        if n_pts < 3:
            continue

        dangling = closure_dangling(subs_pts, tol)
        if dangling:
            continue

        matrix = full_matrix(el, par)
        
        for pts in subs_pts:
            if len(pts) < 3:
                continue
            coords = [(p.real, p.imag) for p in pts]
            
            try:
                poly = Polygon(coords)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                
                if poly.is_empty:
                    continue
                    
                if poly.geom_type == "Polygon":
                    valid_polygons.append(poly)
                elif poly.geom_type == "MultiPolygon":
                    valid_polygons.extend(list(poly.geoms))
            except Exception:
                pass
                
    return valid_polygons


def find_anchor_regions(root: ET.Element) -> List[Polygon]:
    """
    Discover significant geometric regions (anchors) by extracting polygons,
    merging overlapping ones, buffering, and filtering out small artifacts.
    """
    polygons = build_polygons_from_paths(root, JOIN_TOL)
    if not polygons:
        return []

    # Calculate total bounds of all polygons to filter out background frame
    minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')
    for p in polygons:
        px0, py0, px1, py1 = p.bounds
        minx, miny = min(minx, px0), min(miny, py0)
        maxx, maxy = max(maxx, px1), max(maxy, py1)
        
    root_area = (maxx - minx) * (maxy - miny)
    
    filtered_polygons = []
    for p in polygons:
        px0, py0, px1, py1 = p.bounds
        p_area = (px1 - px0) * (py1 - py0)
        if root_area > 0 and (p_area / root_area) >= MAX_BACKGROUND_RATIO:
            continue
        filtered_polygons.append(p)

    if not filtered_polygons:
        return []

    merged = unary_union(filtered_polygons)
    if merged.is_empty:
        return []

    if merged.geom_type == "Polygon":
        parts = [merged]
    elif merged.geom_type == "MultiPolygon":
        parts = [g for g in merged.geoms if not g.is_empty and g.geom_type == "Polygon"]
    else:
        parts = []

    # Buffer slightly to join near components, then filter by minimum area
    anchors = [g.buffer(JOIN_TOL) for g in parts]
    return [g for g in anchors if g.area > AREA_MIN]
