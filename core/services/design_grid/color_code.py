from __future__ import annotations

import re

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_color_code(value: str | None) -> str:
    if not value or not isinstance(value, str):
        raise ValueError("Color code is required!")
    normalized = value.strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"
    if not HEX_COLOR_PATTERN.match(normalized):
        raise ValueError(f"Invalid color code: {value!r}. Expected #RRGGBB.")
    return normalized


def paint_color_code(paint: dict) -> str:
    if not isinstance(paint, dict):
        raise ValueError("Paint must be an object!")
    raw = paint.get("color_code") or paint.get("color_id") or paint.get("hex")
    return normalize_color_code(raw)
