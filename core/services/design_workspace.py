from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.constant import DESIGN_FILE_SEQUENCE, RevisionTypeEnum, StepStatusEnum
from core.models import (
    DesignFile,
    DesignFileRevision,
    DesignWorkspace,
    FileObject,
    PartStep,
)
from core.services.design_grid.snapshot import merge_tiles_into_snapshot


def _previous_file_type(file_type: str) -> str | None:
    try:
        index = DESIGN_FILE_SEQUENCE.index(file_type)
    except ValueError:
        return None
    if index == 0:
        return None
    return DESIGN_FILE_SEQUENCE[index - 1]


def get_file_lock_state(design_file: DesignFile) -> dict:
    previous_type = _previous_file_type(design_file.file_type)
    locked = False
    lock_reason = ""
    if previous_type:
        prev_file = (
            design_file.workspace.files.filter(file_type=previous_type)
            .select_related("official_revision")
            .first()
        )
        if not prev_file or not prev_file.official_revision_id:
            locked = True
            lock_reason = f"Complete {previous_type} before starting {design_file.file_type}."
    return {
        "file_type": design_file.file_type,
        "locked": locked,
        "lock_reason": lock_reason,
        "has_official_revision": bool(design_file.official_revision_id),
    }


@transaction.atomic
def get_or_create_workspace(part_step: PartStep, user=None) -> DesignWorkspace:
    workspace, created = DesignWorkspace.objects.get_or_create(
        part_step=part_step,
        defaults={
            "settings": {"active_file_type": "S1", "progress": {}},
            "updated_by": user,
        },
    )
    if created:
        for file_type in DESIGN_FILE_SEQUENCE:
            DesignFile.objects.create(
                workspace=workspace,
                file_type=file_type,
                updated_by=user,
            )
    return workspace


@transaction.atomic
def initialize_design_workspace(
    *,
    part_step: PartStep,
    grid_width: int,
    grid_height: int,
    snapshot_file: FileObject,
    user=None,
) -> DesignWorkspace:
    workspace = get_or_create_workspace(part_step, user=user)
    s1_file = workspace.files.get(file_type="S1")
    revision = DesignFileRevision.objects.create(
        design_file=s1_file,
        revision_no=1,
        revision_type=RevisionTypeEnum.OFFICIAL.value,
        layers=[],
        grid_width=grid_width,
        grid_height=grid_height,
        snapshot_file=snapshot_file,
        tile_manifest={},
        created_by=user,
    )
    s1_file.latest_revision = revision
    s1_file.official_revision = revision
    s1_file.updated_by = user
    s1_file.save(update_fields=["latest_revision", "official_revision", "updated_by", "modified"])

    workspace.settings = {
        "active_file_type": "S1",
        "progress": {file_type: "not_started" for file_type in DESIGN_FILE_SEQUENCE},
    }
    workspace.settings["progress"]["S1"] = "in_progress"
    workspace.updated_by = user
    workspace.save(update_fields=["settings", "updated_by", "modified"])
    return workspace


@transaction.atomic
def create_design_file_revision(
    *,
    design_file: DesignFile,
    revision_type: int,
    layers: list | None = None,
    grid_width: int | None = None,
    grid_height: int | None = None,
    snapshot_file: FileObject | None = None,
    preview_file: FileObject | None = None,
    tile_manifest: dict | None = None,
    user=None,
    parent_revision=None,
    mark_official: bool = False,
) -> DesignFileRevision:
    if _previous_file_type(design_file.file_type):
        lock = get_file_lock_state(design_file)
        if lock["locked"]:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"file_type": lock["lock_reason"]})

    latest = design_file.latest_revision
    next_no = (latest.revision_no + 1) if latest else 1
    if snapshot_file is None and latest:
        snapshot_file = latest.snapshot_file
    if grid_width is None and latest:
        grid_width = latest.grid_width
    if grid_height is None and latest:
        grid_height = latest.grid_height
    if layers is None and latest:
        layers = latest.layers

    revision = DesignFileRevision.objects.create(
        design_file=design_file,
        revision_no=next_no,
        revision_type=revision_type,
        parent_revision=parent_revision,
        layers=layers or [],
        grid_width=grid_width or 0,
        grid_height=grid_height or 0,
        snapshot_file=snapshot_file,
        preview_file=preview_file,
        tile_manifest=tile_manifest or {},
        created_by=user,
    )
    design_file.latest_revision = revision
    update_fields = ["latest_revision", "updated_by", "modified"]
    if mark_official:
        design_file.official_revision = revision
        update_fields.append("official_revision")
        workspace = design_file.workspace
        progress = dict((workspace.settings or {}).get("progress") or {})
        progress[design_file.file_type] = "done"
        next_index = DESIGN_FILE_SEQUENCE.index(design_file.file_type) + 1
        if next_index < len(DESIGN_FILE_SEQUENCE):
            progress[DESIGN_FILE_SEQUENCE[next_index]] = "in_progress"
            workspace.settings = {
                **(workspace.settings or {}),
                "active_file_type": DESIGN_FILE_SEQUENCE[next_index],
                "progress": progress,
            }
            workspace.save(update_fields=["settings", "modified"])
    design_file.updated_by = user
    design_file.save(update_fields=update_fields)
    return revision


@transaction.atomic
def complete_design_file_revision(
    *,
    revision: DesignFileRevision,
    user=None,
) -> DesignFileRevision:
    merged_snapshot = merge_tiles_into_snapshot(
        snapshot_file=revision.snapshot_file,
        tile_manifest=revision.tile_manifest or {},
        created_by=user,
    )
    revision.snapshot_file = merged_snapshot
    revision.tile_manifest = {}
    revision.revision_type = RevisionTypeEnum.OFFICIAL.value
    revision.save(update_fields=["snapshot_file", "tile_manifest", "revision_type", "modified"])

    design_file = revision.design_file
    design_file.official_revision = revision
    design_file.latest_revision = revision
    design_file.updated_by = user
    design_file.save(update_fields=["official_revision", "latest_revision", "updated_by", "modified"])

    workspace = design_file.workspace
    progress = dict((workspace.settings or {}).get("progress") or {})
    progress[design_file.file_type] = "done"
    next_index = DESIGN_FILE_SEQUENCE.index(design_file.file_type) + 1
    settings = dict(workspace.settings or {})
    if next_index < len(DESIGN_FILE_SEQUENCE):
        progress[DESIGN_FILE_SEQUENCE[next_index]] = "in_progress"
        settings["active_file_type"] = DESIGN_FILE_SEQUENCE[next_index]
    settings["progress"] = progress
    workspace.settings = settings
    workspace.updated_by = user
    workspace.save(update_fields=["settings", "updated_by", "modified"])

    part_step = workspace.part_step
    if design_file.file_type == DESIGN_FILE_SEQUENCE[-1]:
        part_step.status = StepStatusEnum.DONE.value
        part_step.completed_at = timezone.now()
        part_step.updated_by = user
        part_step.save(update_fields=["status", "completed_at", "updated_by", "modified"])

    return revision


@transaction.atomic
def restore_design_file_revision(
    *,
    revision: DesignFileRevision,
    user=None,
) -> DesignFileRevision:
    return create_design_file_revision(
        design_file=revision.design_file,
        revision_type=RevisionTypeEnum.RESTORE.value,
        layers=revision.layers,
        grid_width=revision.grid_width,
        grid_height=revision.grid_height,
        snapshot_file=revision.snapshot_file,
        preview_file=revision.preview_file,
        tile_manifest={},
        user=user,
        parent_revision=revision,
    )


@transaction.atomic
def delete_design_workspace_for_part(part, user=None) -> int:
    part_steps = part.steps.filter(step__code="START_DESIGNING").select_related("design_workspace")
    deleted = 0
    for part_step in part_steps:
        workspace = getattr(part_step, "design_workspace", None)
        if not workspace:
            continue
        for design_file in workspace.files.prefetch_related("revisions"):
            from core.services.file_storage import delete_file_object

            for rev in design_file.revisions.all():
                if rev.snapshot_file_id:
                    delete_file_object(rev.snapshot_file)
                    rev.snapshot_file.delete()
                if rev.preview_file_id:
                    delete_file_object(rev.preview_file)
                    rev.preview_file.delete()
            design_file.revisions.all().delete()
        workspace.files.all().delete()
        workspace.delete()
        deleted += 1
    return deleted
