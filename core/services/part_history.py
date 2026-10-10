from __future__ import annotations

from core.models import Part, PartStep, StepRevision


def upstream_official_revision(part: Part, before_sequence: int) -> StepRevision | None:
    """Official revision of the nearest earlier step. Null when this step is first."""
    previous = (
        PartStep.objects.filter(
            part=part,
            step__sequence__lt=before_sequence,
            official_revision__isnull=False,
        )
        .select_related("official_revision")
        .order_by("-step__sequence")
        .first()
    )
    if not previous:
        return None
    return previous.official_revision


def list_part_history(part: Part) -> list[dict]:
    """StepRevision timeline, newest first. Design-file revisions are not included."""
    step_rows = (
        StepRevision.objects.filter(part_step__part=part)
        .select_related(
            "part_step__step",
            "based_on_revision__part_step__step",
            "created_by",
        )
        .order_by("-created")
    )

    entries: list[dict] = []
    for revision in step_rows:
        based_on = revision.based_on_revision
        entries.append(
            {
                "id": revision.id,
                "step_code": revision.part_step.step.code,
                "step_sequence": revision.part_step.step.sequence,
                "revision_no": revision.revision_no,
                "revision_type": revision.revision_type,
                "parent_revision": revision.parent_revision_id,
                "based_on_revision": revision.based_on_revision_id,
                "based_on_step_code": (
                    based_on.part_step.step.code if based_on else ""
                ),
                "note": revision.note or "",
                "created": revision.created,
                "created_by": revision.created_by_id,
            }
        )
    return entries
