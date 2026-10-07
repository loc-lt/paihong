"""
Raster Renderer — SVG string → PNG bytes (in-memory)
======================================================
Wraps cairosvg to render an SVG string into PNG bytes without touching disk.
Equivalent to api_paihong's a4_svg_to_image.py.
"""

import cairosvg


def svg_to_png_bytes(svg_string: str, dpi: int = 72) -> bytes:
    """
    Render an SVG string to PNG bytes at the given DPI.

    Args:
        svg_string: The SVG content as a string.
        dpi: Dots per inch for rasterisation. SVG user-units are points (1/72 inch).
             Default 72 keeps a 1:1 unit correspondence.

    Returns:
        PNG image as raw bytes.
    """
    scale = dpi / 72.0
    return cairosvg.svg2png(
        bytestring=svg_string.encode("utf-8"),
        background_color="white",
        scale=scale,
    )
