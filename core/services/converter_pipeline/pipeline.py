import xml.etree.ElementTree as ET
from typing import List, Tuple

from core.services.converter_pipeline.path_merger import clean_and_merge_lines
from core.services.converter_pipeline.anchor_detector import find_anchor_regions
from core.services.converter_pipeline.region_splitter import split_by_regions
from core.services.converter_pipeline.constants import JOIN_TOL

def process_svg_string(svg_content: str) -> Tuple[List[str], List[List[str]]]:
    """
    Main orchestrator for SVG geometric processing.
    1. Parse raw SVG string.
    2. Clean and merge fragmented paths.
    3. Detect large geometric anchor regions.
    4. Split elements into multiple SVGs based on regions.
    """
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        return [svg_content], [[]]
        
    # Step 1: Clean open paths and merge them into complete polygons
    clean_and_merge_lines(root, tol=JOIN_TOL)
    
    # Step 2: Detect anchor regions
    regions = find_anchor_regions(root)
    
    if not regions:
        # Fallback if no specific anchors found
        return [ET.tostring(root, encoding="unicode")], [[]]
        
    # Step 3: Split the document by these regions and assign satellites
    split_roots, split_texts = split_by_regions(root, regions)
    
    # Convert element trees back to strings
    return [ET.tostring(r, encoding="unicode") for r in split_roots], split_texts
