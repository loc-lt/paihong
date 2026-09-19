from django.db import transaction

from core.constant import StepStatusEnum
from core.models import Part, PartStep, StepRevision
from core.services.design_workspace import delete_design_workspace_for_part


@transaction.atomic
def clear_steps_after(*, part: Part, after_sequence: int, user=None) -> dict:
    """
    Hard-delete all revisions for steps with sequence greater than after_sequence.
    Used when completing a step after the user went back to redo earlier work.
    """
    part_steps_to_clear = (
        PartStep.objects.filter(
            part=part,
            step__sequence__gt=after_sequence,
        )
        .select_related("step")
        .order_by("step__sequence")
    )

    cleared_steps = []
    deleted_revisions = 0
    deleted_workspaces = delete_design_workspace_for_part(part, user=user)

    for part_step in part_steps_to_clear:
        revision_ids = list(part_step.revisions.values_list("id", flat=True))
        if revision_ids:
            deleted_revisions += len(revision_ids)

            PartStep.objects.filter(
                latest_revision_id__in=revision_ids,
            ).update(latest_revision=None)
            PartStep.objects.filter(
                official_revision_id__in=revision_ids,
            ).update(official_revision=None)

            StepRevision.objects.filter(id__in=revision_ids).delete()

        part_step.status = StepStatusEnum.NOT_STARTED.value
        part_step.started_at = None
        part_step.completed_at = None
        part_step.latest_revision = None
        part_step.official_revision = None
        part_step.updated_by = user
        part_step.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "latest_revision",
                "official_revision",
                "updated_by",
                "modified",
            ]
        )
        cleared_steps.append(
            {
                "step_code": part_step.step.code,
                "step_sequence": part_step.step.sequence,
                "deleted_revisions": len(revision_ids),
            }
        )

    return {
        "cleared_steps": cleared_steps,
        "deleted_revisions": deleted_revisions,
        "deleted_workspaces": deleted_workspaces,
    }
