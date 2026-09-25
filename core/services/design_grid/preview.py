from __future__ import annotations

import io
from collections import defaultdict

from PIL import Image

from core.models import DesignFileRevision, FileObject
from core.services.design_files import is_grid_design_file
from core.services.file_storage import delete_file_object, store_bytes_content
from core.services.design_grid.color_code import normalize_color_code, paint_color_code
from core.services.design_grid.snapshot import _load_snapshot
from core.services.design_grid.tile_codec import decode_tile_bytes
def _hex_to_rgb(color_code: str) -> tuple[int, int, int]:
    normalized = normalize_color_code(color_code)
    return (
        int(normalized[1:3], 16),
        int(normalized[3:5], 16),
        int(normalized[5:7], 16),
    )


def _layer_visibility_maps(layers: list | None) -> tuple[set[str], dict[str, int]]:
    hidden: set[str] = set()
    z_orders: dict[str, int] = {}
    for layer in layers or []:
        if not isinstance(layer, dict):
            continue
        raw_code = layer.get("color_code") or layer.get("color_id") or layer.get("hex")
        try:
            color_code = normalize_color_code(raw_code)
        except ValueError:
            continue
        z_orders[color_code] = int(layer.get("z_order") or 1)
        if layer.get("is_hidden"):
            hidden.add(color_code)
    return hidden, z_orders


def _composite_cell_color(
    paints: list,
    *,
    hidden_colors: set[str],
    z_orders: dict[str, int],
) -> tuple[int, int, int] | None:
    ranked: list[tuple[int, int, str]] = []
    for paint in paints:
        if not isinstance(paint, dict) or paint.get("is_hidden"):
            continue
        try:
            color_code = paint_color_code(paint)
        except ValueError:
            continue
        if color_code in hidden_colors:
            continue
        ranked.append(
            (
                z_orders.get(color_code, 0),
                int(paint.get("order") or 1),
                color_code,
            )
        )
    if not ranked:
        return None
    ranked.sort()
    return _hex_to_rgb(ranked[-1][2])


def create_placeholder_png_file(
    *,
    width: int,
    height: int,
    created_by=None,
    filename: str | None = None,
) -> FileObject:
    if width <= 0 or height <= 0:
        raise ValueError("Placeholder PNG requires positive width and height!")
    image = Image.new("RGB", (width, height), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return store_bytes_content(
        buffer.getvalue(),
        filename=filename or f"placeholder_{width}x{height}.png",
        created_by=created_by,
    )


def render_snapshot_preview_png(
    *,
    snapshot_file: FileObject,
    layers: list | None = None,
    created_by=None,
) -> FileObject:
    """Composite grid tiles + layer panel metadata into a PNG thumbnail."""
    payload = _load_snapshot(snapshot_file)
    width = int(payload.get("width") or 0)
    height = int(payload.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Snapshot grid dimensions are required for preview rendering!")

    hidden_colors, z_orders = _layer_visibility_maps(layers)
    cell_paints: dict[tuple[int, int], list] = defaultdict(list)
    for hex_value in (payload.get("tiles") or {}).values():
        if not isinstance(hex_value, str):
            continue
        try:
            tile = decode_tile_bytes(bytes.fromhex(hex_value))
        except (ValueError, TypeError):
            continue
        for key, paints in (tile.get("cells") or {}).items():
            if not isinstance(key, str) or "," not in key or not isinstance(paints, list):
                continue
            x_str, y_str = key.split(",", 1)
            try:
                x, y = int(x_str), int(y_str)
            except ValueError:
                continue
            if 0 <= x < width and 0 <= y < height:
                cell_paints[(x, y)].extend(paints)

    image = Image.new("RGB", (width, height), (255, 255, 255))
    pixels = image.load()
    for (x, y), paints in cell_paints.items():
        rgb = _composite_cell_color(
            paints,
            hidden_colors=hidden_colors,
            z_orders=z_orders,
        )
        if rgb:
            pixels[x, y] = rgb

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return store_bytes_content(
        buffer.getvalue(),
        filename=f"grid_preview_{width}x{height}.png",
        created_by=created_by,
    )


def refresh_design_file_revision_preview(
    *,
    revision: DesignFileRevision,
    user=None,
    save: bool = True,
) -> DesignFileRevision:
    """Rebuild preview_file from the revision's snapshot tiles and layers[]."""
    if not is_grid_design_file(revision.design_file.file_type):
        return revision

    old_preview = revision.preview_file
    revision.preview_file = render_snapshot_preview_png(
        snapshot_file=revision.snapshot_file,
        layers=revision.layers,
        created_by=user,
    )
    if save:
        revision.save(update_fields=["preview_file", "modified"])
    if old_preview_id := getattr(old_preview, "id", None):
        if revision.preview_file_id and old_preview_id != revision.preview_file_id:
            delete_file_object(old_preview)
            old_preview.delete()
    return revision
