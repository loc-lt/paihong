from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.constant import RevisionTypeEnum, StepStatusEnum
from core.models import (
    DesignFile,
    DesignFileRevision,
    DesignWorkspace,
    FileObject,
    PartStep,
)
from core.services.design_files import (
    DESIGN_FILE_SEQUENCE,
    validate_design_file_complete_order,
)
from core.services.design_grid.preview import refresh_design_file_revision_preview
from core.services.file_storage import delete_file_object_if_unreferenced

def _delete_file_objects(file_object_ids: set) -> None:
    for file_obj in FileObject.objects.filter(pk__in=file_object_ids):
        delete_file_object_if_unreferenced(file_obj)

def _collect_revision_file_object_ids(revisions) -> set:
    file_object_ids: set = set()
    for rev in revisions:
        if rev.snapshot_file_id:
            file_object_ids.add(rev.snapshot_file_id)
        if rev.preview_file_id:
            file_object_ids.add(rev.preview_file_id)
    return file_object_ids


def _clear_design_workspace_revisions(
    workspace: DesignWorkspace,
    *,
    keep_file_object_ids: set | None = None,
) -> None:
    file_object_ids: set = set()
    settings = workspace.settings or {}
    snapshot_id = settings.get("grid_snapshot_id")
    if snapshot_id:
        file_object_ids.add(snapshot_id)

    design_files = list(workspace.files.prefetch_related("revisions"))
    for design_file in design_files:
        file_object_ids.update(
            _collect_revision_file_object_ids(design_file.revisions.all())
        )

    for design_file in design_files:
        DesignFile.objects.filter(pk=design_file.pk).update(
            latest_revision=None,
            official_revision=None,
        )
        design_file.revisions.all().delete()

    workspace.files.filter(is_draft=True).delete()
    _delete_file_objects(file_object_ids - (keep_file_object_ids or set()))

def _next_draft_number(workspace: DesignWorkspace) -> int:
    numbers = []
    for file_type in workspace.files.filter(is_draft=True).values_list("file_type", flat=True):
        suffix = file_type[1:]
        if file_type.startswith("D") and suffix.isdigit():
            numbers.append(int(suffix))
    return max(numbers, default=0) + 1


@transaction.atomic
def create_draft_design_file(
    *,
    workspace: DesignWorkspace,
    name: str,
    width: int,
    height: int,
    user=None,
) -> DesignFile:
    from core.services.design_grid.snapshot import create_empty_grid_snapshot

    number = _next_draft_number(workspace)
    snapshot_file = create_empty_grid_snapshot(
        width=width,
        height=height,
        created_by=user,
    )
    design_file = DesignFile.objects.create(
        workspace=workspace,
        file_type=f"D{number}",
        name=name or f"Draft {number}",
        is_draft=True,
        updated_by=user,
    )
    revision = create_design_file_revision(
        design_file=design_file,
        revision_type=RevisionTypeEnum.MANUAL.value,
        grid_width=width,
        grid_height=height,
        snapshot_file=snapshot_file,
        tile_manifest={},
        user=user,
    )
    if width > 0 and height > 0:
        refresh_design_file_revision_preview(revision=revision, user=user)
    return design_file


@transaction.atomic
def delete_draft_design_file(design_file: DesignFile, user=None) -> None:
    from rest_framework.exceptions import ValidationError

    if not design_file.is_draft:
        raise ValidationError({"file_type": "Only draft files can be deleted!"})
    revisions = list(design_file.revisions.all())
    file_object_ids = _collect_revision_file_object_ids(revisions)
    DesignFile.objects.filter(pk=design_file.pk).update(
        latest_revision=None,
        official_revision=None,
    )
    design_file.revisions.all().delete()
    design_file.delete()
    _delete_file_objects(file_object_ids)


def _ensure_design_files(workspace: DesignWorkspace, user=None) -> None:
    existing = set(workspace.files.values_list("file_type", flat=True))
    for file_type in DESIGN_FILE_SEQUENCE:
        if file_type in existing:
            continue
        DesignFile.objects.create(
            workspace=workspace,
            file_type=file_type,
            updated_by=user,
        )


def _latest_design_file_revision(design_file: DesignFile):
    """Latest revision without tile_manifest. That column can be tens of MB."""
    if not design_file.latest_revision_id:
        return None
    return (
        DesignFileRevision.objects.defer("tile_manifest")
        .filter(pk=design_file.latest_revision_id)
        .first()
    )


def _create_s_grid_revision(
    *,
    s_file: DesignFile,
    width: int,
    height: int,
    snapshot_file: FileObject,
    user=None,
) -> DesignFileRevision:
    revision = DesignFileRevision.objects.create(
        design_file=s_file,
        revision_no=1,
        revision_type=RevisionTypeEnum.MANUAL.value,
        layers=[],
        grid_width=width,
        grid_height=height,
        snapshot_file=snapshot_file,
        tile_manifest={},
        created_by=user,
    )
    refresh_design_file_revision_preview(revision=revision, user=user)
    s_file.latest_revision = revision
    s_file.updated_by = user
    s_file.save(update_fields=["latest_revision", "updated_by", "modified"])
    return revision

@transaction.atomic
def get_or_create_workspace(part_step: PartStep, user=None) -> DesignWorkspace:
    workspace, created = DesignWorkspace.objects.get_or_create(
        part_step=part_step,
        defaults={
            "settings": {
                "active_file_type": "S",
                "progress": {file_type: "not_started" for file_type in DESIGN_FILE_SEQUENCE},
            },
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
    else:
        _ensure_design_files(workspace, user=user)
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
    _clear_design_workspace_revisions(
        workspace,
        keep_file_object_ids={snapshot_file.id},
    )
    s_file = workspace.files.get(file_type="S")
    _create_s_grid_revision(
        s_file=s_file,
        width=grid_width,
        height=grid_height,
        snapshot_file=snapshot_file,
        user=user,
    )

    workspace.settings = {
        "active_file_type": "S",
        "grid": {"width": grid_width, "height": grid_height},
        "progress": {file_type: "not_started" for file_type in DESIGN_FILE_SEQUENCE},
    }
    workspace.settings["progress"]["S"] = "in_progress"
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
    latest = _latest_design_file_revision(design_file)
    next_no = (latest.revision_no + 1) if latest else 1
    if snapshot_file is None and latest:
        snapshot_file = latest.snapshot_file
    if grid_width is None and latest:
        grid_width = latest.grid_width
    if grid_height is None and latest:
        grid_height = latest.grid_height
    if layers is None and latest:
        layers = latest.layers
    if preview_file is None and latest:
        preview_file = latest.preview_file
    if tile_manifest is None:
        tile_manifest = {}

    if snapshot_file is None:
        from rest_framework.exceptions import ValidationError

        raise ValidationError(
            {
                "snapshot_file": (
                    f"Cannot create revision for {design_file.file_type} "
                    "without a snapshot. Complete BUILD_GRID and prior design files first."
                )
            }
        )

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
        tile_manifest=tile_manifest,
        created_by=user,
    )
    design_file.latest_revision = revision
    update_fields = ["latest_revision", "updated_by", "modified"]
    if mark_official:
        design_file.official_revision = revision
        update_fields.append("official_revision")
        if not design_file.is_draft:
            workspace = design_file.workspace
            progress = dict((workspace.settings or {}).get("progress") or {})
            progress[design_file.file_type] = "done"
            workspace.settings = {
                **(workspace.settings or {}),
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
    design_file = revision.design_file
    if not design_file.is_draft:
        validate_design_file_complete_order(
            workspace=design_file.workspace,
            file_type=design_file.file_type,
        )
    revision.revision_type = RevisionTypeEnum.OFFICIAL.value
    revision.tile_manifest = {}
    revision.save(update_fields=["revision_type", "tile_manifest", "modified"])

    design_file.official_revision = revision
    design_file.latest_revision = revision
    design_file.updated_by = user
    design_file.save(update_fields=["official_revision", "latest_revision", "updated_by", "modified"])

    if design_file.is_draft:
        return revision

    workspace = design_file.workspace
    progress = dict((workspace.settings or {}).get("progress") or {})
    progress[design_file.file_type] = "done"
    settings_update = {
        **(workspace.settings or {}),
        "progress": progress,
    }
    if design_file.file_type == "S":
        settings_update["active_file_type"] = "S1"
        if progress.get("S1") == "not_started":
            progress["S1"] = "in_progress"
            settings_update["progress"] = progress
    workspace.settings = settings_update
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
def reopen_design_file(*, design_file: DesignFile, user=None) -> DesignWorkspace:
    """Clear official status from this main file through KMO so it can be edited again."""
    from rest_framework.exceptions import ValidationError

    if design_file.is_draft or design_file.file_type not in DESIGN_FILE_SEQUENCE:
        raise ValidationError(
            {"file_type": "Only main files S-KMO can be reopened!"}
        )
    workspace = design_file.workspace
    progress = dict((workspace.settings or {}).get("progress") or {})
    if progress.get(design_file.file_type) != "done":
        raise ValidationError(
            {"file_type": f"File {design_file.file_type} is not complete!"}
        )

    index = DESIGN_FILE_SEQUENCE.index(design_file.file_type)
    done_types = [
        file_type
        for file_type in DESIGN_FILE_SEQUENCE[index:]
        if progress.get(file_type) == "done"
    ]
    for file_type in done_types:
        progress[file_type] = "in_progress"
    workspace.settings = {
        **(workspace.settings or {}),
        "progress": progress,
        "active_file_type": design_file.file_type,
    }
    workspace.updated_by = user
    workspace.save(update_fields=["settings", "updated_by", "modified"])
    workspace.files.filter(file_type__in=done_types).update(
        official_revision=None,
        updated_by=user,
        modified=timezone.now(),
    )

    part_step = workspace.part_step
    if part_step.status == StepStatusEnum.DONE.value:
        part_step.status = StepStatusEnum.IN_PROGRESS.value
        part_step.completed_at = None
        part_step.updated_by = user
        part_step.save(
            update_fields=["status", "completed_at", "updated_by", "modified"]
        )
    return workspace


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
        _clear_design_workspace_revisions(workspace)
        workspace.files.all().delete()
        workspace.delete()
        deleted += 1
    return deleted

