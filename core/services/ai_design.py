import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.constant import StorageBackendEnum
from core.models import DesignFileRevision

logger = logging.getLogger(__name__)

AI_RECALL_TIMEOUT_SECONDS = 300


def recall_ai(path: str, payload: dict):
    """POST JSON to AI_DOMAIN and return the upstream status and body unchanged."""
    domain = (getattr(settings, "AI_DOMAIN", "") or "").rstrip("/")
    if not domain:
        return Response(
            {"status": False, "message": "AI service is not configured!"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    request = urllib.request.Request(
        f"{domain}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=AI_RECALL_TIMEOUT_SECONDS) as response:
            return _passthrough(
                response.status,
                response.read(),
                response.headers.get("Content-Type", ""),
            )
    except TimeoutError:
        return _timeout_response()
    except urllib.error.HTTPError as exc:
        return _passthrough(exc.code, exc.read(), exc.headers.get("Content-Type", ""))
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            return _timeout_response()
        logger.warning("AI recall failed for %s: %s", path, exc.reason)
        return Response(
            {"status": False, "message": "AI service is unavailable!"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def _passthrough(status_code: int, raw: bytes, content_type: str) -> HttpResponse:
    return HttpResponse(
        raw,
        status=status_code,
        content_type=content_type or "application/json",
    )


def revision_png_path(revision_id) -> str:
    """Render a START_DESIGNING revision snapshot (gzip) to a PNG and return its path."""
    from core.services.design_grid.preview import render_snapshot_preview_png

    try:
        revision = DesignFileRevision.objects.select_related(
            "snapshot_file",
            "design_file__workspace__part_step__step",
        ).get(pk=revision_id)
    except DesignFileRevision.DoesNotExist:
        raise ValidationError({"revision_id": "Design file revision not found!"}) from None

    step = revision.design_file.workspace.part_step.step
    if step.code != "START_DESIGNING":
        raise ValidationError(
            {"revision_id": "Design file revision is not in START_DESIGNING!"}
        )

    try:
        png_file = render_snapshot_preview_png(
            snapshot_file=revision.snapshot_file,
            layers=revision.layers,
        )
    except ValueError as exc:
        raise ValidationError(
            {"revision_id": "Design file revision has no grid image!"}
        ) from exc

    if png_file.storage_backend != StorageBackendEnum.LOCAL.value:
        raise ValidationError(
            {"revision_id": "Revision image must be stored locally to call the AI service!"}
        )
    path = Path(settings.FILE_STORAGE_ROOT) / png_file.storage_key
    if not path.is_file():
        raise ValidationError({"revision_id": "Rendered revision image was not saved!"})
    return str(path)


def _with_optional_gauges(payload: dict, data: dict) -> dict:
    for key in ("wales_per_inch", "courses_per_cm", "courses_per_pixel"):
        if key in data:
            payload[key] = data[key]
    return payload


def recall_smart_s(data: dict):
    payload = _with_optional_gauges(
        {
            "product_code": data["product_code"],
            "path_svg": revision_png_path(data["svg_id"]),
        },
        data,
    )
    return recall_ai("/api/smart_s", payload)


def recall_merge_images(data: dict):
    return recall_ai(
        "/api/merge_images",
        {
            "product_code": data["product_code"],
            "image_paths": [revision_png_path(revision_id) for revision_id in data["image_ids"]],
            "background": data.get("background", "white"),
        },
    )


def recall_create_files_c(data: dict):
    return recall_ai(
        "/api/create_files_c",
        {
            "file_path": revision_png_path(data["file_id"]),
            "product_code": data["product_code"],
        },
    )


def recall_create_file_p(data: dict):
    payload = _with_optional_gauges(
        {
            "product_code": data["product_code"],
            "path_l": revision_png_path(data["l_id"]),
            "path_r": revision_png_path(data["r_id"]),
            "path_l_f": revision_png_path(data["l_f_id"]),
            "path_r_f": revision_png_path(data["r_f_id"]),
        },
        data,
    )
    return recall_ai("/api/create_file_p", payload)


def _timeout_response() -> Response:
    return Response(
        {"status": False, "message": "AI service timed out!"},
        status=status.HTTP_504_GATEWAY_TIMEOUT,
    )
