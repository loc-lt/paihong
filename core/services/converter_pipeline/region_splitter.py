import copy
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

from shapely import affinity
from shapely.geometry import Point, Polygon
from svgpathtools import parse_path

from core.services.converter_pipeline.math_ops import (
    apply_affine_pt, 
    full_matrix, 
    Matrix
)

from core.services.converter_pipeline.constants import EXPAND_REGION_FACTOR, MAX_BACKGROUND_RATIO

def is_background_frame(geom: Polygon, root_bbox: Tuple[float, float, float, float]) -> bool:
    """
    Check if a geometry is likely a background bounding box frame 
    by comparing its area to the total bounds area.
    """
    minx, miny, maxx, maxy = geom.bounds
    geom_area = (maxx - minx) * (maxy - miny)
    
    rminx, rminy, rmaxx, rmaxy = root_bbox
    root_area = (rmaxx - rminx) * (rmaxy - rminy)
    
    if root_area <= 0:
        return False
    return (geom_area / root_area) >= MAX_BACKGROUND_RATIO


def get_total_bounds(drawables: List[Any]) -> Tuple[float, float, float, float]:
    """Calculate the total bounding box for all drawables."""
    minx, miny, maxx, maxy = float('inf'), float('inf'), float('-inf'), float('-inf')
    # Unpack exactly 6 values: el, m, geom, d, kind, gid
    for _, _, geom, _, _, _ in drawables:
        gx0, gy0, gx1, gy1 = geom.bounds
        minx, miny = min(minx, gx0), min(miny, gy0)
        maxx, maxy = max(maxx, gx1), max(maxy, gy1)
    return (minx, miny, maxx, maxy) if minx != float('inf') else (0,0,0,0)


def is_in_defs(el: ET.Element, par: Dict[ET.Element, ET.Element]) -> bool:
    """Check if an element is inside a <defs> or <clipPath> block."""
    curr = par.get(el)
    while curr is not None:
        tag = curr.tag.split("}")[-1]
        if tag in ["defs", "clipPath"]:
            return True
        curr = par.get(curr)
    return False


def split_by_regions(root: ET.Element, regions: List[Polygon]) -> Tuple[List[ET.Element], List[List[str]]]:
    """
    Assigns elements to the closest region (or contained region) and splits the SVG.
    Handles assigning satellite elements (like disconnected text) to the nearest anchor.
    """
    par = {c: p for p in root.iter() for c in p}
    
    # Pre-calculate expanded regions for satellite capture
    regions_exp = [affinity.scale(g, xfact=EXPAND_REGION_FACTOR, yfact=EXPAND_REGION_FACTOR, origin="center") for g in regions]
    
    drawables = []
    
    for el in root.iter():
        if is_in_defs(el, par):
            continue
            
        tag = el.tag.split("}")[-1]
        m = full_matrix(el, par)
        
        if tag == "path":
            d = el.get("d")
            if not d: continue
            try:
                path = parse_path(d)
                xmin, xmax, ymin, ymax = path.bbox()
            except Exception:
                continue
            
            pts = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
            pts_t = [apply_affine_pt(p, m) for p in pts]
            geom = Polygon(pts_t)
            drawables.append((el, m, geom, d, "path", None))
            
        elif tag == "use":
            gid = el.get("{http://www.w3.org/1999/xlink}href") or el.get("href")
            if not gid: continue
            gid = gid.lstrip("#")
            
            # Simplified bbox for use, since definitions might be complex
            # We assume a small box at the use position
            x = float(el.get("x", 0))
            y = float(el.get("y", 0))
            w = float(el.get("width", 10))
            h = float(el.get("height", 10))
            
            pts = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
            pts_t = [apply_affine_pt(p, m) for p in pts]
            geom = Polygon(pts_t)
            drawables.append((el, m, geom, None, "use", gid))
            
        elif tag == "text":
            text_str = "".join(el.itertext()).strip()
            if not text_str: continue
            
            # Simple bbox for text
            x = float(el.get("x", 0))
            y = float(el.get("y", 0))
            font_size = float(el.get("font-size", 12))
            w = len(text_str) * font_size * 0.6
            h = font_size
            
            pts = [(x, y - h), (x+w, y - h), (x+w, y), (x, y)]
            pts_t = [apply_affine_pt(p, m) for p in pts]
            geom = Polygon(pts_t)
            drawables.append((el, m, geom, text_str, "text", None))

    # Calculate overall bounding box to detect background frames
    root_bbox = get_total_bounds(drawables)
    
    # Prepare buckets for each region
    buckets = [ [] for _ in regions ]
    
    for item in drawables:
        el, m, geom, d, kind, gid = item
        
        # Skip elements that look like the full page background bounding box
        if is_background_frame(geom, root_bbox):
            continue
            
        geom_center = Point(geom.centroid)
        best_i = -1
        
        # 1. First pass: strict containment
        for i, reg in enumerate(regions):
            if reg.contains(geom_center) or reg.intersects(geom):
                best_i = i
                break
                
        # 2. Second pass: search within expanded region (satellites)
        if best_i == -1:
            for i, reg_exp in enumerate(regions_exp):
                if reg_exp.contains(geom_center) or reg_exp.intersects(geom):
                    best_i = i
                    break
        
        # 3. Third pass: fallback to the absolute nearest anchor by distance
        if best_i == -1:
            min_dist = float('inf')
            for i, reg in enumerate(regions):
                dist = reg.distance(geom_center)
                if dist < min_dist:
                    min_dist = dist
                    best_i = i
        
        if best_i != -1:
            buckets[best_i].append(item)

    # Reconstruct SVGs and Texts for each bucket
    out_trees = []
    out_texts = []
    
    for b in buckets:
        if not b:
            continue
            
        new_root = ET.Element(root.tag, root.attrib)
        
        # Calculate bounding box for this bucket to tightly crop the detail
        b_minx, b_miny, b_maxx, b_maxy = get_total_bounds(b)
        w = b_maxx - b_minx
        h = b_maxy - b_miny
        
        if w >= 0 and h >= 0:
            pad_x = max(w * 0.05, 5.0)
            pad_y = max(h * 0.05, 5.0)
            v_minx = b_minx - pad_x
            v_miny = b_miny - pad_y
            v_w = w + 2 * pad_x
            v_h = h + 2 * pad_y
            
            new_root.set("viewBox", f"{v_minx} {v_miny} {v_w} {v_h}")
            new_root.set("width", f"{v_w}")
            new_root.set("height", f"{v_h}")
        
        # Copy definition block if it exists
        for child in root:
            if child.tag.split("}")[-1] in ["defs", "style"]:
                new_root.append(copy.deepcopy(child))
                
        # Re-insert the items in the original tree order
        b_elements = {item[0] for item in b}
        
        for el in root.iter():
            if el in b_elements:
                parent = par.get(el)
                # Ensure the path of parents exists in the new tree
                lineage = []
                curr = parent
                while curr is not None and curr != root:
                    lineage.append(curr)
                    curr = par.get(curr)
                lineage.reverse()
                
                insert_target = new_root
                for anc in lineage:
                    # Find or create ancestor
                    found = None
                    for c in insert_target:
                        if c.tag == anc.tag and c.attrib == anc.attrib:
                            found = c
                            break
                    if found is None:
                        found = ET.SubElement(insert_target, anc.tag, anc.attrib)
                    insert_target = found
                
                # Insert a deep copy of the element
                insert_target.append(copy.deepcopy(el))
                
        out_trees.append(new_root)
        
        # Collect texts
        texts = [item[3] for item in b if item[4] == "text"]
        out_texts.append(texts)

    return out_trees, out_texts
