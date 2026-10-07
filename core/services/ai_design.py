import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.constant import StorageBackendEnum
from core.models import DesignFileRevision

logger = logging.getLogger(__name__)

AI_RECALL_TIMEOUT_SECONDS = 300


def _error_response(
    *,
    stage: str,
    message: str,
    http_status: int,
    **details,
) -> Response:
    full_message = f"[{stage}] {message}"
    logger.warning("AI design %s: %s | %s", stage, message, details or {})
    return Response(
        {
            "status": False,
            "message": full_message,
            "data": {"stage": stage, **details},
        },
        status=http_status,
    )


def _decode_body(raw: bytes, limit: int = 4000) -> str:
    text = raw.decode("utf-8", "replace")
    if len(text) > limit:
        return text[:limit] + "…[truncated]"
    return text


def _parse_ai_body(raw: bytes):
    text = _decode_body(raw)
    try:
        return json.loads(text), text
    except json.JSONDecodeError:
        return None, text


def recall_ai(path: str, payload: dict):
    """POST JSON to AI_DOMAIN. Success returns AI body as-is; failures name the stage."""
    domain = (getattr(settings, "AI_DOMAIN", "") or "").rstrip("/")
    if not domain:
        return _error_response(
            stage="config",
            message="AI_DOMAIN is empty. Set AI_DOMAIN in services/revision/.env!",
            http_status=status.HTTP_502_BAD_GATEWAY,
        )

    ai_url = f"{domain}{path}"
    request = urllib.request.Request(
        ai_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=AI_RECALL_TIMEOUT_SECONDS) as response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "") or ""
            if 200 <= response.status < 300:
                parsed, text = _parse_ai_body(raw)
                if parsed is not None:
                    return Response(parsed, status=response.status)
                return _error_response(
                    stage="ai_response",
                    message=f"AI {path} returned {response.status} with a non-JSON body!",
                    http_status=status.HTTP_502_BAD_GATEWAY,
                    ai_path=path,
                    ai_url=ai_url,
                    ai_status=response.status,
                    ai_content_type=content_type,
                    ai_body=text,
                    request_payload=payload,
                )
            return _ai_failure_response(
                path=path,
                ai_url=ai_url,
                status_code=response.status,
                raw=raw,
                content_type=content_type,
                payload=payload,
            )
    except TimeoutError:
        return _error_response(
            stage="ai_timeout",
            message=f"AI {path} timed out after {AI_RECALL_TIMEOUT_SECONDS}s!",
            http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            ai_path=path,
            ai_url=ai_url,
            request_payload=payload,
        )
    except urllib.error.HTTPError as exc:
        return _ai_failure_response(
            path=path,
            ai_url=ai_url,
            status_code=exc.code,
            raw=exc.read(),
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            payload=payload,
        )
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            return _error_response(
                stage="ai_timeout",
                message=f"AI {path} timed out after {AI_RECALL_TIMEOUT_SECONDS}s!",
                http_status=status.HTTP_504_GATEWAY_TIMEOUT,
                ai_path=path,
                ai_url=ai_url,
                request_payload=payload,
            )
        return _error_response(
            stage="ai_connect",
            message=f"Cannot connect to AI {path}!",
            http_status=status.HTTP_502_BAD_GATEWAY,
            ai_path=path,
            ai_url=ai_url,
            reason=str(exc.reason),
            request_payload=payload,
        )


def _ai_failure_response(
    *,
    path: str,
    ai_url: str,
    status_code: int,
    raw: bytes,
    content_type: str,
    payload: dict,
) -> Response:
    parsed, text = _parse_ai_body(raw)
    ai_message = None
    if isinstance(parsed, dict):
        ai_message = parsed.get("message") or parsed.get("detail")
        if isinstance(ai_message, list) and ai_message:
            ai_message = ai_message[0]
    if not ai_message:
        ai_message = text.strip() or f"HTTP {status_code}"

    return _error_response(
        stage="ai_response",
        message=f"AI {path} returned {status_code}: {ai_message}",
        http_status=status.HTTP_502_BAD_GATEWAY,
        ai_path=path,
        ai_url=ai_url,
        ai_status=status_code,
        ai_content_type=content_type or "",
        ai_body=parsed if parsed is not None else text,
        request_payload=payload,
    )


def revision_png_path(revision_id, *, field_name: str = "revision_id") -> str:
    """Render a START_DESIGNING revision snapshot (gzip) to a PNG and return its path."""
    from core.services.design_grid.preview import render_snapshot_preview_png
    from core.services.design_grid.snapshot import _load_snapshot

    try:
        revision = DesignFileRevision.objects.select_related(
            "snapshot_file",
            "design_file__workspace__part_step__step",
        ).get(pk=revision_id)
    except DesignFileRevision.DoesNotExist:
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Design file revision "
                    f"{revision_id} not found!"
                )
            }
        ) from None

    step = revision.design_file.workspace.part_step.step
    if step.code != "START_DESIGNING":
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Revision {revision_id} is not in "
                    f"START_DESIGNING (step={step.code})!"
                )
            }
        )

    try:
        _load_snapshot(revision.snapshot_file)
    except ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, dict):
            detail = next(iter(detail.values()), detail)
        if isinstance(detail, list):
            detail = detail[0] if detail else "Invalid snapshot!"
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Cannot read gzip snapshot for "
                    f"revision {revision_id}: {detail}"
                )
            }
        ) from exc

    try:
        png_file = render_snapshot_preview_png(
            snapshot_file=revision.snapshot_file,
            layers=revision.layers,
        )
    except ValueError as exc:
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Cannot render PNG for revision "
                    f"{revision_id}: {exc}"
                )
            }
        ) from exc
    except Exception as exc:
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Unexpected render error for "
                    f"revision {revision_id}: {type(exc).__name__}: {exc}"
                )
            }
        ) from exc

    if png_file.storage_backend != StorageBackendEnum.LOCAL.value:
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Revision {revision_id} image is not "
                    f"on local storage (backend={png_file.storage_backend})!"
                )
            }
        )
    path = Path(settings.FILE_STORAGE_ROOT) / png_file.storage_key
    if not path.is_file():
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Rendered PNG was not saved at {path}!"
                )
            }
        )
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
            "path_svg": revision_png_path(data["svg_id"], field_name="svg_id"),
        },
        data,
    )
    return recall_ai("/api/smart_s", payload)


def recall_merge_images(data: dict):
    image_paths = []
    for index, revision_id in enumerate(data["image_ids"]):
        image_paths.append(
            revision_png_path(revision_id, field_name=f"image_ids[{index}]")
        )
    return recall_ai(
        "/api/merge_images",
        {
            "product_code": data["product_code"],
            "image_paths": image_paths,
            "background": data.get("background", "white"),
        },
    )


def recall_create_files_c(data: dict):
    return recall_ai(
        "/api/create_files_c",
        {
            "file_path": revision_png_path(data["file_id"], field_name="file_id"),
            "product_code": data["product_code"],
        },
    )


def recall_create_file_p(data: dict):
    payload = _with_optional_gauges(
        {
            "product_code": data["product_code"],
            "path_l": revision_png_path(data["l_id"], field_name="l_id"),
            "path_r": revision_png_path(data["r_id"], field_name="r_id"),
            "path_l_f": revision_png_path(data["l_f_id"], field_name="l_f_id"),
            "path_r_f": revision_png_path(data["r_f_id"], field_name="r_f_id"),
        },
        data,
    )
    return recall_ai("/api/create_file_p", payload)
