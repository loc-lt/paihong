from __future__ import annotations

from django.db.models import Max
from rest_framework.exceptions import ValidationError

from core.constant import StepStatusEnum
from core.models import Part, PartBranch, PartStep, StepRevision
from core.services.file_storage import get_file_url
from core.services.step_settings import unwrap_settings


def _artifact_urls(revision: StepRevision | None) -> list[str]:
    if revision is None:
        return []
    urls = []
    for artifact in revision.artifacts.all():
        file_object = artifact.file
        if file_object:
            urls.append(get_file_url(file_object.storage_key, file_object.storage_backend))
    return urls


def _revisions_by_id(part_id) -> dict:
    return {
        revision.id: revision
        for revision in StepRevision.objects.filter(part_step__part_id=part_id)
        .select_related("part_step__step")
        .prefetch_related("artifacts__file")
    }


def revision_chain(
    head: StepRevision | None,
    by_id: dict | None = None,
) -> list[StepRevision]:
    """Revisions on a branch, earliest step first. Walks based_on_revision."""
    if head is None:
        return []
    if by_id is None:
        by_id = _revisions_by_id(head.part_step.part_id)
    chain = []
    seen = set()
    node = by_id.get(head.id)
    while node is not None and node.id not in seen:
        seen.add(node.id)
        chain.append(node)
        node = by_id.get(node.based_on_revision_id)
    chain.reverse()
    return chain


def _next_branch_number(part: Part) -> int:
    current = PartBranch.objects.filter(part=part).aggregate(Max("number"))["number__max"]
    return (current or 0) + 1


def apply_branch(part: Part, branch: PartBranch, user=None) -> PartBranch:
    """Point every PartStep at this branch. Revisions on other branches stay."""
    path = revision_chain(branch.head_revision)
    by_step = {revision.part_step_id: revision for revision in path}
    part_steps = list(part.steps.select_related("step"))
    for part_step in part_steps:
        revision = by_step.get(part_step.id)
        if revision is not None:
            part_step.status = StepStatusEnum.DONE.value
            part_step.official_revision = revision
            part_step.latest_revision = revision
            part_step.started_at = revision.created
            part_step.completed_at = revision.created
        else:
            part_step.status = StepStatusEnum.NOT_STARTED.value
            part_step.official_revision = None
            part_step.latest_revision = None
            part_step.started_at = None
            part_step.completed_at = None
        part_step.updated_by = user
        part_step.save(
            update_fields=[
                "status",
                "official_revision",
                "latest_revision",
                "started_at",
                "completed_at",
                "updated_by",
                "modified",
            ]
        )
    part.current_branch = branch
    part.save(update_fields=["current_branch", "modified"])
    return branch


def checkout_branch(part: Part, branch: PartBranch, user=None) -> PartBranch:
    if branch.part_id != part.id:
        raise ValidationError({"branch_id": "Branch does not belong to this part!"})
    return apply_branch(part, branch, user)


def attach_official_revision(part: Part, revision: StepRevision, user=None) -> PartBranch:
    """Extend the checked-out branch, or fork when this step is already on it."""
    part = Part.objects.select_related("current_branch").get(pk=part.pk)
    branch = part.current_branch
    if branch is None or branch.head_revision_id is None:
        branch = PartBranch.objects.create(
            part=part,
            number=_next_branch_number(part),
            head_revision=revision,
        )
        return apply_branch(part, branch, user)

    path = revision_chain(branch.head_revision)
    on_path = any(item.part_step_id == revision.part_step_id for item in path)
    if on_path:
        branch = PartBranch.objects.create(
            part=part,
            number=_next_branch_number(part),
            head_revision=revision,
        )
    else:
        branch.head_revision = revision
        branch.save(update_fields=["head_revision", "modified"])
    return apply_branch(part, branch, user)


def _history_step(part_step: PartStep, revision: StepRevision | None) -> dict:
    """One workflow step on a branch. Steps the branch has not reached stay not started."""
    if revision is not None:
        return {
            "id": revision.id,
            "step_code": part_step.step.code,
            "step_sequence": part_step.step.sequence,
            "status": StepStatusEnum.DONE.value,
            "revision_no": revision.revision_no,
            "revision_type": revision.revision_type,
            "note": revision.note or "",
            "settings": unwrap_settings(revision.settings)[0],
            "file_urls": _artifact_urls(revision),
            "created": revision.created,
        }
    return {
        "id": None,
        "step_code": part_step.step.code,
        "step_sequence": part_step.step.sequence,
        "status": StepStatusEnum.NOT_STARTED.value,
        "revision_no": None,
        "revision_type": None,
        "note": "",
        "settings": {},
        "file_urls": [],
        "created": None,
    }


def _part_steps(part: Part) -> list[PartStep]:
    return list(part.steps.select_related("step").order_by("step__sequence"))


def _branch_row(part_steps: list[PartStep], branch: PartBranch, by_id: dict) -> dict:
    on_branch = {
        revision.part_step_id: revision
        for revision in revision_chain(branch.head_revision, by_id)
    }
    return {
        "id": branch.id,
        "number": branch.number,
        "steps": [
            _history_step(part_step, on_branch.get(part_step.id))
            for part_step in part_steps
        ],
    }


def list_part_branches(part: Part) -> dict:
    part_steps = _part_steps(part)
    by_id = _revisions_by_id(part.id)
    branches = PartBranch.objects.filter(part=part).select_related("head_revision").order_by("number")
    return {
        "current_branch_id": part.current_branch_id,
        "branches": [_branch_row(part_steps, branch, by_id) for branch in branches],
    }
