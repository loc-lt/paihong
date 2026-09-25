from __future__ import annotations

import json
from typing import Any

from core.services.design_grid.color_code import normalize_color_code, paint_color_code


def normalize_paint(paint: dict) -> dict:
    return {
        "color_code": paint_color_code(paint),
        "order": int(paint.get("order") or 1),
        "is_hidden": bool(paint.get("is_hidden", False)),
    }


def normalize_tile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Tile payload must be a JSON object!")
    cells = payload.get("cells")
    if cells is None:
        raise ValueError("Tile payload must include 'cells'!")
    if not isinstance(cells, dict):
        raise ValueError("Tile 'cells' must be an object!")
    normalized_cells: dict[str, list] = {}
    for key, paints in cells.items():
        if not isinstance(key, str) or "," not in key:
            raise ValueError(f"Invalid cell key: {key!r}. Expected 'x,y'.")
        if not isinstance(paints, list):
            raise ValueError(f"Cell {key!r} must contain a paint array!")
        normalized_cells[key] = [normalize_paint(paint) for paint in paints]
    return {"v": int(payload.get("v") or 1), "cells": normalized_cells}


def normalize_layers(layers: list | None) -> list:
    if not layers:
        return []
    if not isinstance(layers, list):
        raise ValueError("Layers must be an array!")
    normalized = []
    for index, layer in enumerate(layers, start=1):
        if not isinstance(layer, dict):
            raise ValueError("Each layer must be an object!")
        raw_code = layer.get("color_code") or layer.get("color_id") or layer.get("hex")
        normalized.append(
            {
                "color_code": normalize_color_code(raw_code),
                "name": str(layer.get("name") or ""),
                "z_order": int(layer.get("z_order") or index),
                "is_hidden": bool(layer.get("is_hidden", False)),
                "is_lock": bool(layer.get("is_lock", False)),
            }
        )
    return normalized


def decode_tile_bytes(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Tile data must be UTF-8 JSON!") from exc
    return normalize_tile_payload(payload)


def encode_tile_bytes(payload: dict[str, Any]) -> bytes:
    normalized = normalize_tile_payload(payload)
    return json.dumps(normalized, separators=(",", ":")).encode("utf-8")


def normalize_tile_update_bytes(raw: bytes) -> bytes:
    return encode_tile_bytes(decode_tile_bytes(raw))
