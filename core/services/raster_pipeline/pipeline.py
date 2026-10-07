"""
Raster Pipeline Orchestrator
=============================
Runs the full raster-based region-detection pipeline on a single SVG string:

  0. preprocess_svg     — <use>→<path>, bake transforms, normalise strokes,
                          remove background quads
  1. svg_to_png_bytes   — render SVG → PNG at 72 DPI (in-memory, no disk I/O)
  2. label_png_bytes    — fill enclosed areas + connected-component labelling
  3. group_paths        — map SVG paths to pixel regions
  4. crop_svg_element   — crop each region SVG and translate to origin (0,0)

Returns the same (list_svg, list_texts) tuple as the vector pipeline so both
converters share the same response schema.
"""

import xml.etree.ElementTree as ET
from typing import List, Tuple

from core.services.raster_pipeline.svg_preprocessor import preprocess_svg
from core.services.raster_pipeline.raster_renderer import svg_to_png_bytes
from core.services.raster_pipeline.region_labeler import label_png_bytes
from core.services.raster_pipeline.region_grouper import group_paths_by_region
from core.services.raster_pipeline.svg_cropper import crop_svg_element


def process_svg_raster(svg_content: str) -> Tuple[List[str], List[List[str]]]:
    """
    Full raster pipeline: SVG string → list of per-region SVG strings.

    Args:
        svg_content: Raw SVG as a string (from PDF page or DXF render).

    Returns:
        (list_svg, list_texts)
        list_svg   — one SVG string per detected region
        list_texts — empty lists (raster pipeline does not extract text)
    """
    try:
        # Step 0: Preprocess SVG (normalise for raster rendering)
        cleaned_svg = preprocess_svg(svg_content)

        # Step 1: Render to PNG
        png_bytes = svg_to_png_bytes(cleaned_svg, dpi=72)

        # Step 2: Label pixel regions
        _label_png, labels, areas, n_regions = label_png_bytes(png_bytes)

        if n_regions == 0:
            return [svg_content], [[]]

        img_h, img_w = labels.shape

        # Step 3: Map SVG paths to pixel regions
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.fromstring(cleaned_svg)
        region_elements, list_texts = group_paths_by_region(root, labels, areas, img_h, img_w)

        if not region_elements:
            return [svg_content], [[]]

        # Step 4: Crop each region SVG to its tight bounding box
        out_svgs: List[str] = []
        for region_el in region_elements:
            cropped = crop_svg_element(region_el)
            out_svgs.append(ET.tostring(cropped, encoding="unicode"))

        return out_svgs, list_texts

    except Exception as exc:
        # Graceful fallback: return the original SVG unchanged
        return [svg_content], [[]]
