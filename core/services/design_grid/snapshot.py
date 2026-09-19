from __future__ import annotations

import gzip
import json
import struct
from typing import Any

from core.constant import GRID_SNAPSHOT_SCHEMA_VERSION, GRID_TILE_SIZE
from core.models import FileObject
from core.services.file_storage import read_file_object_bytes, store_bytes_content

TILE_HEADER_FMT = ">II"


def _tile_key(tx: int, ty: int) -> str:
    return f"{tx}_{ty}"


def _empty_tile_bytes() -> bytes:
    return b""


def create_empty_grid_snapshot(
    *,
    width: int,
    height: int,
    layers: list[dict] | None = None,
    created_by=None,
) -> FileObject:
    payload = {
        "schema_version": GRID_SNAPSHOT_SCHEMA_VERSION,
        "width": width,
        "height": height,
        "tile_size": GRID_TILE_SIZE,
        "layers": layers or [],
        "tiles": {},
    }
    content = gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return store_bytes_content(
        content,
        filename=f"grid_snapshot_{width}x{height}.json.gz",
        created_by=created_by,
    )


def _load_snapshot(file_object: FileObject) -> dict[str, Any]:
    raw = read_file_object_bytes(file_object)
    try:
        decompressed = gzip.decompress(raw)
    except OSError:
        decompressed = raw
    return json.loads(decompressed.decode("utf-8"))


def _dump_snapshot(payload: dict[str, Any]) -> bytes:
    return gzip.compress(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def read_tiles_from_snapshot(
    *,
    snapshot_file: FileObject,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> dict[str, str]:
    payload = _load_snapshot(snapshot_file)
    tile_size = int(payload.get("tile_size") or GRID_TILE_SIZE)
    tiles = payload.get("tiles") or {}
    result: dict[str, str] = {}
    for ty in range(y0 // tile_size, (max(y0, y1 - 1)) // tile_size + 1):
        for tx in range(x0 // tile_size, (max(x0, x1 - 1)) // tile_size + 1):
            key = _tile_key(tx, ty)
            tile_data = tiles.get(key)
            if tile_data is None:
                continue
            if isinstance(tile_data, str):
                result[key] = tile_data
            else:
                result[key] = tile_data.hex() if isinstance(tile_data, bytes) else str(tile_data)
    return result


def write_tiles_to_snapshot(
    *,
    snapshot_file: FileObject,
    tile_updates: dict[str, bytes | str],
    created_by=None,
) -> FileObject:
    payload = _load_snapshot(snapshot_file)
    tiles = payload.setdefault("tiles", {})
    for key, value in tile_updates.items():
        if isinstance(value, str):
            tiles[key] = value
        else:
            tiles[key] = value.hex()
    content = _dump_snapshot(payload)
    return store_bytes_content(
        content,
        filename=f"grid_snapshot_{payload.get('width')}x{payload.get('height')}.json.gz",
        created_by=created_by,
    )


def merge_tiles_into_snapshot(
    *,
    snapshot_file: FileObject,
    tile_manifest: dict[str, str],
    created_by=None,
) -> FileObject:
    if not tile_manifest:
        return snapshot_file
    payload = _load_snapshot(snapshot_file)
    tiles = payload.setdefault("tiles", {})
    tiles.update(tile_manifest)
    content = _dump_snapshot(payload)
    return store_bytes_content(
        content,
        filename=f"grid_snapshot_{payload.get('width')}x{payload.get('height')}_merged.json.gz",
        created_by=created_by,
    )


def encode_tile_rle(values: list[int]) -> bytes:
    if not values:
        return _empty_tile_bytes()
    chunks: list[tuple[int, int]] = []
    current = values[0]
    count = 1
    for value in values[1:]:
        if value == current and count < 65535:
            count += 1
        else:
            chunks.append((current, count))
            current = value
            count = 1
    chunks.append((current, count))
    out = bytearray()
    for value, count in chunks:
        out.extend(struct.pack(TILE_HEADER_FMT, int(value) & 0xFFFFFFFF, count))
    return bytes(out)
