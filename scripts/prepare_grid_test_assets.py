#!/usr/bin/env python3
"""Normalize FE grid export into BE test assets (color_code hex, tile_size=64)."""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

TILE_SIZE_DEFAULT = 64
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


def normalize_paint(paint: dict) -> dict:
    raw = paint.get("color_code") or paint.get("color_id") or paint.get("hex")
    return {
        "color_code": normalize_color_code(raw),
        "order": int(paint.get("order") or 1),
        "is_hidden": bool(paint.get("is_hidden", False)),
    }


def normalize_layers(layers: list) -> list:
    normalized = []
    for index, layer in enumerate(layers, start=1):
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


def _tile_key(x: int, y: int, tile_size: int) -> str:
    return f"{x // tile_size}_{y // tile_size}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="FE export JSON path")
    parser.add_argument("out_dir", type=Path, help="Output directory")
    parser.add_argument("--tile-size", type=int, default=TILE_SIZE_DEFAULT)
    args = parser.parse_args()

    data = json.loads(args.source.read_text(encoding="utf-8"))
    width = int(data["gridWidth"])
    height = int(data["gridHeight"])
    raw_cells = (data.get("cells") or {}).get("cells") or {}
    tile_size = args.tile_size

    tiles_by_key: dict[str, dict[str, list]] = defaultdict(dict)
    unique_hex: set[str] = set()
    for key, paints in raw_cells.items():
        x_str, y_str = key.split(",", 1)
        x, y = int(x_str), int(y_str)
        norm = [normalize_paint(paint) for paint in paints]
        for paint in norm:
            unique_hex.add(paint["color_code"])
        tiles_by_key[_tile_key(x, y, tile_size)][key] = norm

    layers = normalize_layers(
        [
            {
                "color_code": hex_val,
                "name": f"Layer {hex_val}",
                "z_order": index,
                "is_hidden": True,
                "is_lock": True,
            }
            for index, hex_val in enumerate(sorted(unique_hex), start=1)
        ]
    )

    patch_tiles = []
    for tile_key in sorted(
        tiles_by_key.keys(),
        key=lambda item: (int(item.split("_")[1]), int(item.split("_")[0])),
    ):
        payload = {"v": 1, "cells": tiles_by_key[tile_key]}
        tile_b64 = base64.b64encode(
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        patch_tiles.append({"key": tile_key, "data": tile_b64})

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "layers.json").write_text(json.dumps(layers, indent=2), encoding="utf-8")
    (args.out_dir / "build_grid_settings.json").write_text(
        json.dumps({"grid": {"width": width, "height": height}}, indent=2),
        encoding="utf-8",
    )
    (args.out_dir / "patch_tiles.json").write_text(
        json.dumps({"tiles": patch_tiles}, indent=2),
        encoding="utf-8",
    )

    stats: Counter[str] = Counter()
    for paints in raw_cells.values():
        for paint in paints:
            stats[normalize_paint(paint)["color_code"]] += 1

    fe_tiles = data.get("tiles", {}).get("tiles", [])
    expected_tile_count = math.ceil(width / tile_size) * math.ceil(height / tile_size)
    (args.out_dir / "grid_meta.json").write_text(
        json.dumps(
            {
                "gridWidth": width,
                "gridHeight": height,
                "tileSize": tile_size,
                "cellCount": len(raw_cells),
                "uniqueColors": sorted(unique_hex),
                "tileCountForBE": len(patch_tiles),
                "tileKeys": [item["key"] for item in patch_tiles],
                "expectedMaxTiles": expected_tile_count,
                "feTileCount": len(fe_tiles),
                "paintField": "color_code",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.out_dir / "color_stats.json").write_text(
        json.dumps(dict(stats.most_common()), indent=2),
        encoding="utf-8",
    )
    print(
        f"Wrote assets to {args.out_dir} "
        f"({len(raw_cells)} cells, {len(layers)} layers, {len(patch_tiles)} tiles @ {tile_size})"
    )


if __name__ == "__main__":
    main()
