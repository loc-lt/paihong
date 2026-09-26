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
    is_grid_design_file,
    validate_design_file_complete_order,
)
from core.services.design_grid.preview import (
    create_placeholder_png_file,
    refresh_design_file_revision_preview,
)
from core.services.design_grid.snapshot import merge_tiles_into_snapshot
from core.services.file_storage import delete_file_object

def _delete_file_objects(file_object_ids: set) -> None:
    for file_id in file_object_ids:
        file_obj = FileObject.objects.filter(pk=file_id).first()
        if not file_obj:
            continue
        delete_file_object(file_obj)
        file_obj.delete()

def _clear_design_file_revisions(design_file: DesignFile) -> None:
    file_object_ids: set = set()
    for rev in design_file.revisions.all():
        if rev.snapshot_file_id:
            file_object_ids.add(rev.snapshot_file_id)
        if rev.preview_file_id:
            file_object_ids.add(rev.preview_file_id)
    DesignFile.objects.filter(pk=design_file.pk).update(
        latest_revision=None,
        official_revision=None,
    )
    design_file.revisions.all().delete()
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


def _create_s_placeholder_revision(
    *,
    s_file: DesignFile,
    width: int,
    height: int,
    user=None,
) -> DesignFileRevision:
    if s_file.revisions.exists():
        _clear_design_file_revisions(s_file)
    png = create_placeholder_png_file(
        width=width,
        height=height,
        created_by=user,
        filename=f"design_{s_file.file_type}_{width}x{height}.png",
    )
    revision = DesignFileRevision.objects.create(
        design_file=s_file,
        revision_no=1,
        revision_type=RevisionTypeEnum.MANUAL.value,
        layers=[],
        grid_width=width,
        grid_height=height,
        snapshot_file=png,
        preview_file=png,
        tile_manifest={},
        created_by=user,
    )
    s_file.latest_revision = revision
    s_file.updated_by = user
    s_file.save(update_fields=["latest_revision", "updated_by", "modified"])
    return revision


def _ensure_s_design_file_revision(workspace: DesignWorkspace, user=None) -> DesignFileRevision | None:
    """Backfill file S when BUILD_GRID only created S1 (legacy workspaces)."""
    s_file = workspace.files.filter(file_type="S").first()
    if not s_file or s_file.latest_revision_id:
        return None
    s1_file = (
        workspace.files.filter(file_type="S1")
        .select_related("latest_revision")
        .first()
    )
    if not s1_file or not s1_file.latest_revision:
        return None
    source = s1_file.latest_revision
    width = int(source.grid_width or 0)
    height = int(source.grid_height or 0)
    if width <= 0 or height <= 0:
        return None
    return _create_s_placeholder_revision(
        s_file=s_file,
        width=width,
        height=height,
        user=user,
    )


def _pending_grid_snapshot(workspace: DesignWorkspace) -> FileObject | None:
    settings = workspace.settings or {}
    snapshot_id = settings.get("grid_snapshot_id")
    if not snapshot_id:
        return None
    return FileObject.objects.filter(pk=snapshot_id).first()


def initialize_s1_design_file(*, workspace: DesignWorkspace, user=None) -> DesignFileRevision | None:
    """Create S1 grid revision from BUILD_GRID snapshot (after S is ready or complete)."""
    s1_file = workspace.files.filter(file_type="S1").first()
    if not s1_file or s1_file.latest_revision_id:
        return None

    settings = workspace.settings or {}
    grid = settings.get("grid") or {}
    width = int(grid.get("width") or 0)
    height = int(grid.get("height") or 0)
    snapshot_file = _pending_grid_snapshot(workspace)
    if not snapshot_file or width <= 0 or height <= 0:
        return None

    revision = DesignFileRevision.objects.create(
        design_file=s1_file,
        revision_no=1,
        revision_type=RevisionTypeEnum.MANUAL.value,
        layers=[],
        grid_width=width,
        grid_height=height,
        snapshot_file=snapshot_file,
        tile_manifest={},
        created_by=user,
    )
    s1_file.latest_revision = revision
    s1_file.updated_by = user
    s1_file.save(update_fields=["latest_revision", "updated_by", "modified"])
    return revision


def _ensure_s1_design_file_revision(workspace: DesignWorkspace, user=None) -> DesignFileRevision | None:
    """Backfill S1 when S is done but grid revision was deferred (new BUILD_GRID flow)."""
    progress = dict((workspace.settings or {}).get("progress") or {})
    if progress.get("S") != "done":
        return None
    return initialize_s1_design_file(workspace=workspace, user=user)

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
    _ensure_s_design_file_revision(workspace, user=user)
    _ensure_s1_design_file_revision(workspace, user=user)
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
    s_file = workspace.files.get(file_type="S")
    s1_file = workspace.files.get(file_type="S1")
    if s1_file.revisions.exists():
        _clear_design_file_revisions(s1_file)
    _create_s_placeholder_revision(
        s_file=s_file,
        width=grid_width,
        height=grid_height,
        user=user,
    )

    workspace.settings = {
        "active_file_type": "S",
        "grid": {"width": grid_width, "height": grid_height},
        "grid_snapshot_id": str(snapshot_file.id),
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
    if preview_file is None and latest:
        preview_file = latest.preview_file
    if tile_manifest is None and latest:
        tile_manifest = dict(latest.tile_manifest or {})
    elif tile_manifest is None:
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
    validate_design_file_complete_order(
        workspace=design_file.workspace,
        file_type=design_file.file_type,
    )
    revision.revision_type = RevisionTypeEnum.OFFICIAL.value
    update_fields = ["revision_type", "modified"]
    if is_grid_design_file(design_file.file_type):
        merged_snapshot = merge_tiles_into_snapshot(
            snapshot_file=revision.snapshot_file,
            tile_manifest=revision.tile_manifest or {},
            created_by=user,
        )
        revision.snapshot_file = merged_snapshot
        revision.tile_manifest = {}
        update_fields.extend(["snapshot_file", "tile_manifest"])
    else:
        revision.tile_manifest = {}
        update_fields.append("tile_manifest")
    revision.save(update_fields=update_fields)
    refresh_design_file_revision_preview(revision=revision, user=user)

    design_file.official_revision = revision
    design_file.latest_revision = revision
    design_file.updated_by = user
    design_file.save(update_fields=["official_revision", "latest_revision", "updated_by", "modified"])

    workspace = design_file.workspace
    progress = dict((workspace.settings or {}).get("progress") or {})
    progress[design_file.file_type] = "done"
    settings_update = {
        **(workspace.settings or {}),
        "progress": progress,
    }
    if design_file.file_type == "S":
        initialize_s1_design_file(workspace=workspace, user=user)
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
            _clear_design_file_revisions(design_file)
        workspace.files.all().delete()
        workspace.delete()
        deleted += 1
    return deleted

