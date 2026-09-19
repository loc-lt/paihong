from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from core.constant import STEP_SETTINGS_POLICY

SETTINGS_WRAPPER_VERSION = 1


def get_settings_policy(step_code: str) -> dict:
    return deepcopy(STEP_SETTINGS_POLICY.get(step_code, {"has_settings": False}))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_wrapped_settings(settings: dict | None) -> bool:
    if not isinstance(settings, dict):
        return False
    return "data" in settings and isinstance(settings.get("data"), dict)


def unwrap_settings(settings: dict | None) -> tuple[dict, dict]:
    if not settings:
        return {}, {}
    if is_wrapped_settings(settings):
        data = settings.get("data") or {}
        meta = settings.get("meta") or {}
        return deepcopy(data), deepcopy(meta)
    return deepcopy(settings), {}


def wrap_settings(
    data: dict | None,
    *,
    source: str = "manual",
    from_step_code: str = "",
    from_revision_id: str = "",
    schema_version: int = SETTINGS_WRAPPER_VERSION,
    extra_meta: dict | None = None,
) -> dict:
    meta: dict[str, Any] = {
        "source": source,
        "schema_version": schema_version,
        "generated_at": _utc_now_iso(),
    }
    if from_step_code:
        meta["from_step_code"] = from_step_code
    if from_revision_id:
        meta["from_revision_id"] = from_revision_id
    if extra_meta:
        meta.update(extra_meta)
    return {
        "data": deepcopy(data or {}),
        "meta": meta,
    }


def normalize_incoming_settings(settings: dict | None, *, default_source: str = "manual") -> dict:
    if not settings:
        return wrap_settings({}, source=default_source)
    if is_wrapped_settings(settings):
        data, meta = unwrap_settings(settings)
        if not meta.get("source"):
            meta["source"] = default_source
        if "schema_version" not in meta:
            meta["schema_version"] = SETTINGS_WRAPPER_VERSION
        if "generated_at" not in meta:
            meta["generated_at"] = _utc_now_iso()
        return {"data": data, "meta": meta}
    return wrap_settings(settings, source=default_source)


def settings_data_for_validation(settings: dict | None) -> dict:
    data, _meta = unwrap_settings(settings)
    return data


def merge_validated_data(
    validated_data: dict,
    *,
    source: str = "manual",
    from_step_code: str = "",
    from_revision_id: str = "",
    extra_meta: dict | None = None,
) -> dict:
    return wrap_settings(
        validated_data,
        source=source,
        from_step_code=from_step_code,
        from_revision_id=from_revision_id,
        extra_meta=extra_meta,
    )
