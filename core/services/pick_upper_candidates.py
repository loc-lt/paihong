from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from core.services.file_storage import read_file_object_bytes


def _parse_svg_dimensions(svg_content: str) -> tuple[float, float]:
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        return 0.0, 0.0

    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])

    width = root.get("width", "0").replace("mm", "").replace("px", "").strip()
    height = root.get("height", "0").replace("mm", "").replace("px", "").strip()
    try:
        return float(width or 0), float(height or 0)
    except ValueError:
        return 0.0, 0.0


def _parse_label_metadata(label: str) -> dict:
    side = ""
    variant = ""
    size_class = ""
    med = False
    lat = False

    if "左" in label:
        side = "left"
    elif "右" in label:
        side = "right"

    size_match = re.search(r"(\d+)", label)
    if size_match:
        variant = size_match.group(1)

    if "大" in label:
        size_class = "large"
    elif "小" in label:
        size_class = "small"

    upper = label.upper()
    med = "MED" in upper or "中" in label
    lat = "LAT" in upper or "侧" in label

    return {
        "side": side,
        "variant": variant,
        "size_class": size_class,
        "med": med,
        "lat": lat,
    }


def build_pick_upper_candidates(
    *,
    part,
    preview_artifact_id: str | None = None,
) -> list[dict]:
    detected = part.detected_metadata or {}
    existing = detected.get("pick_upper_candidates")
    if existing:
        return existing

    width_mm, height_mm = 0.0, 0.0
    if part.preview_file_id:
        try:
            svg_bytes = read_file_object_bytes(part.preview_file)
            width_mm, height_mm = _parse_svg_dimensions(svg_bytes.decode("utf-8", errors="ignore"))
        except Exception:
            pass

    bbox = part.source_bbox or {}
    label = detected.get("label") or part.name or ""
    parsed = _parse_label_metadata(label)

    candidate = {
        "index": 0,
        "med": parsed["med"],
        "lat": parsed["lat"],
        "size": detected.get("size"),
        "width_mm": width_mm or float(bbox.get("w") or 0),
        "height_mm": height_mm or float(bbox.get("h") or 0),
        "label": label,
        "side": parsed["side"],
        "variant": parsed["variant"],
        "size_class": parsed["size_class"],
        "suggested_rotation_deg": detected.get("suggested_rotation_deg", 0),
        "preview_artifact_id": preview_artifact_id,
        "bbox": {
            "x": float(bbox.get("x") or 0),
            "y": float(bbox.get("y") or 0),
            "w": float(bbox.get("w") or width_mm),
            "h": float(bbox.get("h") or height_mm),
        },
    }
    return [candidate]


def build_bootstrap_pick_upper_settings(part, preview_artifact_id: str | None = None) -> dict:
    candidates = build_pick_upper_candidates(
        part=part,
        preview_artifact_id=preview_artifact_id,
    )
    suggested = candidates[0].get("suggested_rotation_deg") if candidates else 0
    return {
        "selected_candidate_index": 0,
        "rotation": float(suggested or 0),
        "candidates": candidates,
    }
