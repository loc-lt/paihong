import hashlib
import json
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.constant import (
    AUTOSAVE_KEEP_LATEST,
    STEP_SETTINGS_SOURCE_BOOTSTRAP,
    RevisionTypeEnum,
    StepStatusEnum,
)
from core.exceptions import RevisionConflict
from core.models import PartStep, RevisionArtifact, StepRevision
from core.services.file_storage import store_uploaded_file
from core.services.step_handlers.base import run_step_complete_handler
from core.services.step_settings import unwrap_settings
from core.serializers.step_settings_serializers import validate_step_settings


@dataclass
class StepRevisionResult:
    revision: StepRevision
    next_step_settings: dict | None = None


def _settings_hash(settings_data: dict) -> str:
    data, _meta = unwrap_settings(settings_data)
    normalized = json.dumps(data or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _next_revision_no(part_step: PartStep) -> int:
    current = part_step.revisions.aggregate(max_no=Max("revision_no")).get("max_no")
    return (current or 0) + 1


def _cleanup_autosaves(part_step: PartStep) -> None:
    autosaves = (
        part_step.revisions.filter(revision_type=RevisionTypeEnum.AUTOSAVE.value)
        .order_by("-revision_no")
    )
    stale_ids = list(autosaves.values_list("id", flat=True)[AUTOSAVE_KEEP_LATEST:])
    if stale_ids:
        StepRevision.objects.filter(id__in=stale_ids).delete()


def _validate_base_revision(part_step: PartStep, base_revision_id):
    if not base_revision_id:
        return
    latest = part_step.latest_revision_id
    if str(latest) != str(base_revision_id):
        raise RevisionConflict(
            {"base_revision_id": "Revision conflict. Please reload and try again!"}
        )


@transaction.atomic
def create_step_revision(
    *,
    part_step: PartStep,
    revision_type: int,
    settings: dict,
    artifacts=None,
    user=None,
    parent_revision=None,
    base_revision_id=None,
    app_version="",
    note="",
    settings_schema_version=1,
    mark_step_in_progress=True,
    mark_step_done=False,
    settings_source: str = "manual",
) -> StepRevision | StepRevisionResult:
    step_code = part_step.step.code
    schema_key = part_step.step.settings_schema_key or step_code
    validated_settings = validate_step_settings(
        step_code,
        settings or {},
        schema_key,
        default_source=settings_source,
    )
    settings_digest = _settings_hash(validated_settings)

    if not mark_step_done:
        _validate_base_revision(part_step, base_revision_id)

    if (
        revision_type == RevisionTypeEnum.AUTOSAVE.value
        and part_step.latest_revision
        and part_step.latest_revision.settings_hash == settings_digest
        and not artifacts
    ):
        if mark_step_done:
            return StepRevisionResult(
                revision=part_step.latest_revision,
                next_step_settings=None,
            )
        return part_step.latest_revision

    revision = StepRevision.objects.create(
        part_step=part_step,
        revision_no=_next_revision_no(part_step),
        revision_type=revision_type,
        parent_revision=parent_revision,
        settings=validated_settings,
        settings_schema_version=settings_schema_version,
        app_version=app_version,
        settings_hash=settings_digest,
        created_by=user,
        note=note,
    )

    for index, artifact in enumerate(artifacts or []):
        uploaded = artifact.get("file")
        file_object = artifact.get("file_object")
        if uploaded and not file_object:
            file_object = store_uploaded_file(uploaded, created_by=user)
        if not file_object:
            continue

        filename = artifact.get("filename") or ""
        if not filename and uploaded:
            filename = uploaded.name or ""

        RevisionArtifact.objects.create(
            revision=revision,
            file=file_object,
            filename=filename,
            role=artifact["role"],
            sequence=artifact.get("sequence", index),
            metadata=artifact.get("metadata") or {},
        )

    part_step.latest_revision = revision
    update_fields = ["latest_revision", "updated_by", "modified"]

    if revision_type == RevisionTypeEnum.OFFICIAL.value:
        part_step.official_revision = revision
        update_fields.append("official_revision")

    if mark_step_in_progress and part_step.status == StepStatusEnum.NOT_STARTED.value:
        part_step.status = StepStatusEnum.IN_PROGRESS.value
        part_step.started_at = timezone.now()
        update_fields.extend(["status", "started_at"])

    if mark_step_done:
        part_step.status = StepStatusEnum.DONE.value
        part_step.completed_at = timezone.now()
        update_fields.extend(["status", "completed_at"])

    part_step.updated_by = user
    part_step.save(update_fields=update_fields)

    if revision_type == RevisionTypeEnum.AUTOSAVE.value:
        _cleanup_autosaves(part_step)

    if mark_step_done:
        next_step_settings = run_step_complete_handler(
            part_step=part_step,
            revision=revision,
            user=user,
        )
        from core.services.part_revert import clear_steps_after

        clear_steps_after(
            part=part_step.part,
            after_sequence=part_step.step.sequence,
            user=user,
        )
        return StepRevisionResult(
            revision=revision,
            next_step_settings=next_step_settings,
        )

    return revision


@transaction.atomic
def restore_revision(*, revision: StepRevision, user=None, base_revision_id=None):
    part_step = revision.part_step
    return create_step_revision(
        part_step=part_step,
        revision_type=RevisionTypeEnum.RESTORE.value,
        settings=revision.settings,
        artifacts=[
            {
                "file_object": artifact.file,
                "filename": artifact.filename,
                "role": artifact.role,
                "sequence": artifact.sequence,
                "metadata": artifact.metadata,
            }
            for artifact in revision.artifacts.select_related("file")
        ],
        user=user,
        parent_revision=revision,
        base_revision_id=base_revision_id,
        settings_schema_version=revision.settings_schema_version,
        app_version=revision.app_version,
        note=f"Restored from revision {revision.revision_no}",
    )
