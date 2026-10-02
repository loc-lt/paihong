from __future__ import annotations

import base64
import gzip
import io
import json
from typing import Any

from core.services.design_grid.color_code import normalize_color_code, paint_color_code


def normalize_paint(paint: dict) -> dict:
    return {
        "color_code": paint_color_code(paint),
        "order": int(paint.get("order") or 1),
        "is_hidden": bool(paint.get("is_hidden", False)),
        "is_lock": bool(paint.get("is_lock", False)),
    }


def _parse_cell_key(key: str) -> tuple[int, int]:
    x_str, _, y_str = key.partition(",")
    try:
        return int(x_str), int(y_str)
    except ValueError as exc:
        raise ValueError(f"Invalid cell key: {key!r}. Expected 'x,y' integers.") from exc


def validate_tile_origin(
    *,
    tile_key: str,
    grid_width: int,
    grid_height: int,
    tile_size: int,
) -> None:
    tx_str, _, ty_str = tile_key.partition("_")
    tx, ty = int(tx_str), int(ty_str)
    if tx * tile_size >= grid_width or ty * tile_size >= grid_height:
        raise ValueError(
            f"Tile {tile_key} is outside the {grid_width}x{grid_height} grid!"
        )


def validate_tile_bounds(
    *,
    tile_key: str,
    payload: dict[str, Any],
    grid_width: int,
    grid_height: int,
    tile_size: int,
) -> None:
    validate_tile_origin(
        tile_key=tile_key,
        grid_width=grid_width,
        grid_height=grid_height,
        tile_size=tile_size,
    )
    for key in payload.get("cells") or {}:
        x, y = _parse_cell_key(key)
        if not (0 <= x < grid_width and 0 <= y < grid_height):
            raise ValueError(
                f"Cell {key!r} is outside the {grid_width}x{grid_height} grid!"
            )


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


_GZIP_MAGIC = b"\x1f\x8b"
_MAX_TILE_JSON_BYTES = 32 * 1024 * 1024


def _tile_json_bytes(raw: bytes) -> bytes:
    """Accept raw JSON or gzip(JSON). Only the bytes of this one tile are inflated."""
    if raw[:2] != _GZIP_MAGIC:
        return raw
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            data = gz.read(_MAX_TILE_JSON_BYTES + 1)
    except OSError as exc:
        raise ValueError("Tile gzip data is invalid!") from exc
    if len(data) > _MAX_TILE_JSON_BYTES:
        raise ValueError("Tile JSON exceeds 32 MB after decompression!")
    return data


def decode_tile_bytes(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(_tile_json_bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Tile data must be UTF-8 JSON, or gzip of that JSON!") from exc
    return normalize_tile_payload(payload)


def encode_tile_bytes(payload: dict[str, Any]) -> bytes:
    normalized = normalize_tile_payload(payload)
    return json.dumps(normalized, separators=(",", ":")).encode("utf-8")


_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def stored_tile_bytes(value: str) -> bytes:
    """Bytes of a snapshot tile. New values are base64; older values are hex."""
    if value and len(value) % 2 == 0 and all(char in _HEX_DIGITS for char in value):
        return bytes.fromhex(value)
    return base64.b64decode(value)


def normalize_tile_update_bytes(raw: bytes) -> bytes:
    return encode_tile_bytes(decode_tile_bytes(raw))
