from __future__ import annotations

import math

from rest_framework.exceptions import ValidationError

from core.models import PartStep
from core.services.step_settings import unwrap_settings


def _canvas_measurements(part_step: PartStep) -> tuple[float, float]:
    canvas_step = (
        part_step.part.steps.select_related("official_revision", "step")
        .filter(step__code="CANVAS_FRAME_MEASURE", official_revision__isnull=False)
        .first()
    )
    if not canvas_step or not canvas_step.official_revision:
        return 0.0, 0.0
    data, _meta = unwrap_settings(canvas_step.official_revision.settings)
    canvas = data.get("canvas") or {}
    return float(canvas.get("width_mm") or 0), float(canvas.get("height_mm") or 0)


def compute_grid_pixels(settings_data: dict) -> dict:
    needle_density = int(settings_data.get("needle_density") or 0)
    cos_number = int(settings_data.get("cos_number") or 0)
    course_per_pixel = int(settings_data.get("course_per_pixel") or 0)
    source = settings_data.get("source_measurements_mm") or {}
    width_mm = float(source.get("width") or 0)
    height_mm = float(source.get("height") or 0)

    if needle_density <= 0 or cos_number <= 0 or course_per_pixel <= 0:
        raise ValidationError(
            {
                "settings": [
                    "Needle density, cos number, and course per pixel must be positive!"
                ]
            }
        )
    if width_mm <= 0 or height_mm <= 0:
        raise ValidationError(
            {
                "settings": [
                    "Source measurements must be positive! Complete canvas frame measure first."
                ]
            }
        )

    width = max(1, int(math.floor(width_mm * needle_density / cos_number / course_per_pixel)))
    height = max(1, int(math.floor(height_mm * needle_density / cos_number / course_per_pixel)))
    return {"width": width, "height": height}


def build_enter_specs_settings(settings_data: dict, *, part_step: PartStep) -> dict:
    width_mm, height_mm = _canvas_measurements(part_step)
    if width_mm <= 0 or height_mm <= 0:
        source = settings_data.get("source_measurements_mm") or {}
        width_mm = float(source.get("width") or 0)
        height_mm = float(source.get("height") or 0)

    merged = {
        **settings_data,
        "source_measurements_mm": {"width": width_mm, "height": height_mm},
    }
    grid_pixels = try_compute_grid_pixels(merged)
    if grid_pixels:
        merged["grid_pixels"] = grid_pixels
    return merged


def try_compute_grid_pixels(settings_data: dict) -> dict | None:
    try:
        return compute_grid_pixels(settings_data)
    except ValidationError:
        return None
