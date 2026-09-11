from django.db import transaction

from core.constant import (
    BOOTSTRAP_ARTIFACT_ROLES,
    BOOTSTRAP_DONE_STEP_CODES,
    BOOTSTRAP_STEP_SETTINGS,
    RevisionTypeEnum,
    StepStatusEnum,
)
from core.models import Part, PartStep, TemplateStep, WorkItem, WorkflowTemplate


def get_default_workflow_template() -> WorkflowTemplate | None:
    return (
        WorkflowTemplate.objects.filter(is_active=True, is_default=True).first()
        or WorkflowTemplate.objects.filter(is_active=True).order_by("code").first()
    )


def get_workflow_template_for_part(part: Part) -> WorkflowTemplate | None:
    work_item = part.work_item
    if work_item.workflow_template_id:
        return work_item.workflow_template
    return get_default_workflow_template()


def get_template_steps(template: WorkflowTemplate):
    return (
        TemplateStep.objects.filter(template=template, step__is_active=True)
        .select_related("step")
        .order_by("sequence")
    )


@transaction.atomic
def initialize_part_steps(part: Part, user=None) -> list[PartStep]:
    template = get_workflow_template_for_part(part)
    if not template:
        return []

    created_steps = []
    for template_step in get_template_steps(template):
        part_step, _created = PartStep.objects.get_or_create(
            part=part,
            step=template_step.step,
            defaults={
                "status": StepStatusEnum.NOT_STARTED.value,
                "updated_by": user,
            },
        )
        created_steps.append(part_step)
    return created_steps


def _bootstrap_artifacts(part: Part, step_code: str) -> list[dict]:
    part = (
        Part.objects.select_related(
            "preview_file",
            "source_document__file",
        )
        .filter(pk=part.pk)
        .first()
    )
    if not part:
        return []

    if step_code == "RECEIVE_FILES":
        source_document = part.source_document
        if source_document.file_id:
            return [
                {
                    "file_object": source_document.file,
                    "filename": source_document.original_filename,
                    "role": BOOTSTRAP_ARTIFACT_ROLES["RECEIVE_FILES"],
                    "sequence": 0,
                    "metadata": {"source_document_id": str(source_document.id)},
                }
            ]
        return []

    if step_code == "PICK_UPPER" and part.preview_file_id:
        return [
            {
                "file_object": part.preview_file,
                "filename": part.name or "preview",
                "role": BOOTSTRAP_ARTIFACT_ROLES["PICK_UPPER"],
                "sequence": 0,
                "metadata": {"part_id": str(part.id)},
            }
        ]
    return []


@transaction.atomic
def bootstrap_completed_part_steps(
    part: Part,
    user=None,
    step_codes=BOOTSTRAP_DONE_STEP_CODES,
) -> list[PartStep]:
    from core.services.step_revision import create_step_revision

    completed = []
    for code in step_codes:
        part_step = (
            part.steps.select_related("step")
            .filter(step__code=code)
            .first()
        )
        if not part_step or part_step.status == StepStatusEnum.DONE.value:
            if part_step:
                completed.append(part_step)
            continue

        create_step_revision(
            part_step=part_step,
            revision_type=RevisionTypeEnum.OFFICIAL.value,
            settings=BOOTSTRAP_STEP_SETTINGS.get(code, {}),
            artifacts=_bootstrap_artifacts(part, code),
            user=user,
            note=f"Auto-completed during work item processing ({code}).",
            mark_step_in_progress=True,
            mark_step_done=True,
        )
        part_step.refresh_from_db()
        completed.append(part_step)
    return completed


@transaction.atomic
def sync_part_steps(part: Part, user=None) -> list[PartStep]:
    template = get_workflow_template_for_part(part)
    if not template:
        return list(part.steps.all())

    synced = []
    for template_step in get_template_steps(template):
        part_step, _created = PartStep.objects.get_or_create(
            part=part,
            step=template_step.step,
            defaults={
                "status": StepStatusEnum.NOT_STARTED.value,
                "updated_by": user,
            },
        )
        synced.append(part_step)
    return synced


@transaction.atomic
def sync_work_item_parts(work_item: WorkItem, user=None) -> int:
    count = 0
    for source in work_item.source_documents.prefetch_related("parts"):
        for part in source.parts.all():
            sync_part_steps(part, user=user)
            count += 1
    return count


@transaction.atomic
def ensure_work_item_template(work_item: WorkItem) -> WorkItem:
    if work_item.workflow_template_id:
        return work_item
    default_template = get_default_workflow_template()
    if default_template:
        work_item.workflow_template = default_template
        work_item.save(update_fields=["workflow_template", "modified"])
    return work_item
