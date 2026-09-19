"""
Bridge from CHECK_COLORS settings to CANVAS_FRAME_MEASURE settings.

Replace stub logic with real AI integration when available.
"""

from __future__ import annotations

from core.models import StepRevision
from core.services.step_settings import unwrap_settings


def derive_canvas_frame_settings(
    *,
    check_colors_settings: dict | None = None,
    revision: StepRevision | None = None,
) -> dict:
    if revision and not check_colors_settings:
        check_colors_settings, _meta = unwrap_settings(revision.settings)

    check_colors_settings = check_colors_settings or {}
    frame_expansion_mm = float(check_colors_settings.get("frame_expansion_mm") or 0)

    width_mm = 206.0 + frame_expansion_mm * 2
    height_mm = 252.7 + frame_expansion_mm * 2

    layers = check_colors_settings.get("layers") or {}
    outer = layers.get("outer_contour") or {}
    line_ids = outer.get("line_ids") or []
    measured_line_count = sum(
        len((layer or {}).get("line_ids") or [])
        for layer in layers.values()
        if isinstance(layer, dict)
    )

    return {
        "canvas": {"width_mm": width_mm, "height_mm": height_mm},
        "origin": {"x": 0.0, "y": 0.0},
        "scale": 1.0,
        "basis": {
            "outer_contour_line_count": len(line_ids),
            "measured_line_count": measured_line_count,
            "center_cross_included": bool(layers.get("center_cross")),
        },
    }
