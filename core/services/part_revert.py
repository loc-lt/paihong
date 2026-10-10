from django.db import transaction

from core.constant import StepStatusEnum
from core.models import Part, PartStep


@transaction.atomic
def clear_steps_after(*, part: Part, after_sequence: int, user=None) -> dict:
    """
    Mark every later step not started.

    Revisions, artifacts, and the START_DESIGNING workspace stay. latest_revision
    and official_revision stay so the saved work is still readable.
    """
    part_steps = list(
        PartStep.objects.filter(
            part=part,
            step__sequence__gt=after_sequence,
        )
        .select_related("step")
        .order_by("step__sequence")
    )

    reset_steps = []
    for part_step in part_steps:
        part_step.status = StepStatusEnum.NOT_STARTED.value
        part_step.started_at = None
        part_step.completed_at = None
        part_step.updated_by = user
        part_step.save(
            update_fields=[
                "status",
                "started_at",
                "completed_at",
                "updated_by",
                "modified",
            ]
        )
        reset_steps.append(
            {
                "step_code": part_step.step.code,
                "step_sequence": part_step.step.sequence,
            }
        )

    return {"reset_steps": reset_steps}
