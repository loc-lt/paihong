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
_AI_OUTPUT_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".svg",
    ".tif",
    ".tiff",
    ".kmo",
}


class AiOutputFileError(Exception):
    def __init__(self, message: str, source_path: str):
        super().__init__(message)
        self.source_path = source_path


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
                    try:
                        parsed = publish_ai_output_images(parsed)
                    except AiOutputFileError as exc:
                        return _error_response(
                            stage="ai_files",
                            message=str(exc),
                            http_status=status.HTTP_502_BAD_GATEWAY,
                            ai_path=path,
                            ai_url=ai_url,
                            source_path=exc.source_path,
                            request_payload=payload,
                        )
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


def _ai_output_root() -> str:
    return (getattr(settings, "AI_OUTPUT_ROOT", "") or "/home/devserver/paihong/ai").rstrip("/")


def fetch_ai_json(path: str, payload: dict) -> dict:
    """POST JSON to AI_DOMAIN and return the parsed body. Raises ValidationError."""
    domain = (getattr(settings, "AI_DOMAIN", "") or "").rstrip("/")
    if not domain:
        raise ValidationError(
            {"ai": "AI_DOMAIN is empty. Set AI_DOMAIN in the service .env!"}
        )
    ai_url = f"{domain}{path}"
    request = urllib.request.Request(
        ai_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=AI_RECALL_TIMEOUT_SECONDS) as response:
            parsed, text = _parse_ai_body(response.read())
    except TimeoutError as exc:
        raise ValidationError(
            {"ai": f"AI {path} timed out after {AI_RECALL_TIMEOUT_SECONDS}s!"}
        ) from exc
    except urllib.error.HTTPError as exc:
        parsed, text = _parse_ai_body(exc.read())
        message = None
        if isinstance(parsed, dict):
            message = parsed.get("message") or parsed.get("detail")
        raise ValidationError(
            {"ai": f"AI {path} returned {exc.code}: {message or text.strip() or 'request failed'}"}
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            raise ValidationError(
                {"ai": f"AI {path} timed out after {AI_RECALL_TIMEOUT_SECONDS}s!"}
            ) from exc
        raise ValidationError(
            {"ai": f"Cannot connect to AI {path}!"}
        ) from exc

    if not isinstance(parsed, dict):
        raise ValidationError({"ai": f"AI {path} returned a non-JSON body!"})
    if parsed.get("status") not in ("success", True):
        raise ValidationError(
            {"ai": str(parsed.get("message") or f"AI {path} did not succeed!")}
        )
    return parsed


def store_ai_output_file(value: str, *, created_by=None):
    """Copy one AI output file into object storage, keeping its original filename."""
    from core.services.file_storage import store_unique_bytes

    root = _ai_output_root()
    if not isinstance(value, str) or not value.startswith(root + "/"):
        raise AiOutputFileError(f"AI output path is outside {root}: {value}", str(value))
    if Path(value).suffix.lower() not in _AI_OUTPUT_SUFFIXES:
        raise AiOutputFileError(f"AI output file type is not stored: {value}", value)
    file_path = Path(value)
    if not file_path.is_file():
        raise AiOutputFileError(
            (
                f"Cannot read AI output image at {value}. "
                f"Mount {root} into this service at the same path."
            ),
            value,
        )
    return store_unique_bytes(
        file_path.read_bytes(),
        filename=file_path.name,
        created_by=created_by,
    )


def _publish_ai_image_path(value: str) -> str:
    """Copy one AI image into object storage as {sha256}_{original filename}."""
    from core.services.file_storage import get_file_url

    root = _ai_output_root()
    if not value.startswith(root + "/"):
        return value
    if Path(value).suffix.lower() not in _AI_OUTPUT_SUFFIXES:
        return value
    file_path = Path(value)
    stored = store_ai_output_file(value)
    url = get_file_url(stored.storage_key, stored.storage_backend)
    if not url or not str(url).startswith(("http://", "https://")):
        raise AiOutputFileError(
            f"Stored {file_path.name} but BE_DOMAIN did not produce a public URL (got {url!r}).",
            value,
        )
    return url


def publish_ai_output_images(node):
    """Replace AI filesystem image paths with this service's media URLs. Other fields stay."""
    if isinstance(node, str):
        return _publish_ai_image_path(node)
    if isinstance(node, list):
        return [publish_ai_output_images(item) for item in node]
    if isinstance(node, dict):
        return {key: publish_ai_output_images(value) for key, value in node.items()}
    return node


def revision_png_url(revision_id, *, field_name: str = "revision_id") -> str:
    """Render a START_DESIGNING revision snapshot to PNG and return its public media URL."""
    from core.services.design_grid.preview import refresh_design_file_revision_preview
    from core.services.design_grid.snapshot import _load_snapshot
    from core.services.file_storage import get_file_url

    be_domain = (getattr(settings, "BE_DOMAIN", "") or "").rstrip("/")
    if not be_domain:
        raise ValidationError(
            {
                field_name: (
                    "[config] BE_DOMAIN is empty. Set BE_DOMAIN in "
                    "services/revision/.env so AI receives a full image URL!"
                )
            }
        )

    try:
        revision = DesignFileRevision.objects.select_related(
            "snapshot_file",
            "preview_file",
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
        revision = refresh_design_file_revision_preview(revision=revision)
        png_file = revision.preview_file
        if png_file is None:
            raise ValueError("Preview PNG was not stored on the revision.")
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

    disk_path = Path(settings.FILE_STORAGE_ROOT) / png_file.storage_key
    if png_file.storage_backend == StorageBackendEnum.LOCAL.value and not disk_path.is_file():
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Rendered PNG was not saved at "
                    f"{disk_path}!"
                )
            }
        )

    url = get_file_url(png_file.storage_key, png_file.storage_backend)
    if not url or not url.startswith(("http://", "https://")):
        raise ValidationError(
            {
                field_name: (
                    f"[render_png][{field_name}] Could not build a full public URL "
                    f"for revision {revision_id} (got {url!r})!"
                )
            }
        )
    return url


# Keep the old name for any remaining imports.
revision_png_path = revision_png_url


def _with_optional_gauges(payload: dict, data: dict) -> dict:
    for key in ("wales_per_inch", "courses_per_cm", "courses_per_pixel"):
        if key in data:
            payload[key] = data[key]
    return payload


def recall_smart_s(data: dict):
    return recall_ai_passthrough("/api/v1/smart_s", data)


def recall_merge_images(data: dict):
    list_url_images = []
    for index, revision_id in enumerate(data["list_image_ids"]):
        list_url_images.append(
            revision_png_url(revision_id, field_name=f"list_image_ids[{index}]")
        )
    return recall_ai(
        "/api/v1/merge_images",
        {
            "product_code": data["product_code"],
            "list_url_images": list_url_images,
            "background": data.get("background", "white"),
        },
    )


def recall_create_files_c(data: dict):
    return recall_ai(
        "/api/v1/create_files_c",
        {
            "product_code": data["product_code"],
            "url_image": revision_png_url(data["image_id"], field_name="image_id"),
        },
    )


def recall_create_file_p(data: dict):
    payload = _with_optional_gauges(
        {
            "product_code": data["product_code"],
            "url_l": revision_png_url(data["l_id"], field_name="l_id"),
            "url_r": revision_png_url(data["r_id"], field_name="r_id"),
            "url_l_f": revision_png_url(data["l_f_id"], field_name="l_f_id"),
            "url_r_f": revision_png_url(data["r_f_id"], field_name="r_f_id"),
        },
        data,
    )
    return recall_ai("/api/v1/create_file_p", payload)


def recall_ai_passthrough(path: str, data: dict):
    """Forward the validated FE body to AI without rewriting paths."""
    return recall_ai(path, dict(data))


def recall_split_regions(data: dict):
    return recall_ai_passthrough("/api/v1/split_regions", data)


def recall_rotate_svg(data: dict):
    return recall_ai_passthrough("/api/v1/rotate_svg", data)


def recall_delete_paths(data: dict):
    return recall_ai_passthrough("/api/v1/delete_paths", data)


def recall_delete_anchors(data: dict):
    return recall_ai_passthrough("/api/v1/delete_anchors", data)


def recall_color_paths(data: dict):
    return recall_ai_passthrough("/api/v1/color_paths", data)


def recall_create_train_db(data: dict):
    return recall_ai_passthrough("/api/v1/create_train_db", data)


def recall_create_train_db_anchor(data: dict):
    return recall_ai_passthrough("/api/v1/create_train_db_anchor", data)


def recall_edge_binding(data: dict):
    colors = {
        name: {"rgb": list(item["rgb"])}
        for name, item in data["colors"].items()
    }
    return recall_ai(
        "/api/v1/edge_binding",
        {
            "url_file": revision_png_url(data["file_id"], field_name="file_id"),
            "code_product": data["code_product"],
            "colors": colors,
            "type": data["type"],
        },
    )


def recall_create_file_fc(data: dict):
    payload = {
        "product_code": data["product_code"],
        "count": data["count"],
        "url_image": revision_png_url(data["image_id"], field_name="image_id"),
    }
    if "type_machine" in data:
        payload["type_machine"] = data["type_machine"]
    return recall_ai("/api/v1/create_file_fc", payload)


def _copy_present(data: dict, keys: tuple[str, ...]) -> dict:
    return {key: data[key] for key in keys if key in data}


def recall_auto_job(data: dict):
    payload = _copy_present(data, ("product_code", "type_machine", "number_jackquard"))
    payload["url_image"] = revision_png_url(data["image_id"], field_name="image_id")
    return recall_ai("/api/v1/auto_job", payload)


def recall_combine_fc(data: dict):
    return recall_ai(
        "/api/v1/combine_fc",
        {
            "product_code": data["product_code"],
            "url_ff": revision_png_url(data["ff_id"], field_name="ff_id"),
            "url_fb": revision_png_url(data["fb_id"], field_name="fb_id"),
            "ff_has_hole": data.get("ff_has_hole", False),
            "fb_has_hole": data.get("fb_has_hole", False),
        },
    )


def recall_shift_odd_rows(data: dict):
    return recall_ai(
        "/api/v1/shift_odd_rows",
        {
            "url_image": revision_png_url(data["image_id"], field_name="image_id"),
            "value": data["value"],
        },
    )


def recall_create_kmo(data: dict):
    payload = {
        key: value
        for key, value in data.items()
        if key not in ("file_jc_id", "file_f_id")
    }
    payload["url_file_jc"] = revision_png_url(
        data["file_jc_id"], field_name="file_jc_id"
    )
    payload["url_file_f"] = revision_png_url(
        data["file_f_id"], field_name="file_f_id"
    )
    return recall_ai("/api/v1/create_kmo", payload)
