"""
SVG Cropper — Crop + Translate-to-Origin (in-memory)
=====================================================
Equivalent to api_paihong a7_crop_svg.py.

Takes an SVG ET.Element (already preprocessed) and returns a new element
with viewBox tightly cropped around the contained paths and all path
coordinates translated so the top-left corner sits at (0, 0).
"""

import xml.etree.ElementTree as ET
from svgelements import Path, Matrix

SVG_NS = "http://www.w3.org/2000/svg"

# Extra padding (in SVG user units) added around the tight bounding box
CROP_PAD = 0.0


def _content_bbox(
    path_elements: list[ET.Element],
) -> tuple[float, float, float, float] | None:
    """
    Compute the combined bounding box (xmin, ymin, xmax, ymax) of all paths.
    Returns None if no valid bounding box could be found.
    """
    xmin = ymin = float("inf")
    xmax = ymax = float("-inf")
    found = False

    for el in path_elements:
        d = el.get("d")
        if not d:
            continue
        try:
            bb = Path(d).bbox()
        except Exception:
            bb = None
        if not bb:
            continue
        x0, y0, x1, y1 = bb
        xmin = min(xmin, x0)
        ymin = min(ymin, y0)
        xmax = max(xmax, x1)
        ymax = max(ymax, y1)
        found = True

    if not found:
        return None
    return xmin, ymin, xmax, ymax


def crop_svg_element(svg_element: ET.Element, pad: float = CROP_PAD) -> ET.Element:
    """
    Crop an SVG element to the tight bounding box of its paths and translate
    all path coordinates so the detail starts at (0, 0).

    Args:
        svg_element : An ET.Element representing an <svg> root.
        pad         : Optional uniform padding (in user units) added to each side.

    Returns:
        The same element, modified in-place, with updated viewBox/width/height
        and translated path 'd' attributes.
    """
    path_els = [el for el in svg_element.iter(f"{{{SVG_NS}}}path") if el.get("d")]
    bb = _content_bbox(path_els)

    if bb is None:
        return svg_element

    xmin, ymin, xmax, ymax = bb
    xmin -= pad
    ymin -= pad
    xmax += pad
    ymax += pad
    width = max(xmax - xmin, 1e-9)
    height = max(ymax - ymin, 1e-9)

    # Translate all paths to origin
    shift = Matrix.translate(-xmin, -ymin)
    for el in path_els:
        d = el.get("d")
        if d:
            try:
                el.set("d", (Path(d) * shift).d())
            except Exception:
                pass

    svg_element.set("width", f"{width:.6f}")
    svg_element.set("height", f"{height:.6f}")
    svg_element.set("viewBox", f"0 0 {width:.6f} {height:.6f}")

    return svg_element
