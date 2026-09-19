from __future__ import annotations

from typing import Protocol

from core.constant import STEP_SETTINGS_POLICY
from core.models import PartStep, StepRevision
from core.services.step_settings import merge_validated_data


class StepCompleteHandler(Protocol):
    step_code: str

    def on_complete(
        self,
        *,
        part_step: PartStep,
        revision: StepRevision,
        user=None,
    ) -> dict | None:
        """
        Return next_step_settings dict or None:
        {
            "step_code": "...",
            "settings": { "data": ..., "meta": ... },
        }
        """


_HANDLERS: dict[str, StepCompleteHandler] = {}


def register_handler(handler: StepCompleteHandler) -> None:
    _HANDLERS[handler.step_code] = handler


def get_step_complete_handler(step_code: str) -> StepCompleteHandler | None:
    return _HANDLERS.get(step_code)


def _next_step_code(current_code: str) -> str | None:
    from core.models import WorkflowStepDefinition

    current = WorkflowStepDefinition.objects.filter(code=current_code).first()
    if not current:
        return None
    nxt = (
        WorkflowStepDefinition.objects.filter(
            sequence=current.sequence + 1,
            is_active=True,
        )
        .order_by("sequence")
        .first()
    )
    return nxt.code if nxt else None


def run_step_complete_handler(
    *,
    part_step: PartStep,
    revision: StepRevision,
    user=None,
) -> dict | None:
    step_code = part_step.step.code
    handler = get_step_complete_handler(step_code)
    if handler:
        result = handler.on_complete(part_step=part_step, revision=revision, user=user)
        if result:
            return result

    policy = STEP_SETTINGS_POLICY.get(step_code, {})
    on_complete = policy.get("on_complete") or {}
    propagate_to = on_complete.get("propagate_to")
    if not propagate_to:
        return None

    next_code = propagate_to
    next_policy = STEP_SETTINGS_POLICY.get(next_code, {})
    if not next_policy.get("has_settings"):
        return None

    return {
        "step_code": next_code,
        "settings": merge_validated_data(
            {},
            source=on_complete.get("via", "propagated"),
            from_step_code=step_code,
            from_revision_id=str(revision.id),
        ),
    }


def _register_defaults() -> None:
    from core.services.step_handlers import (
        build_grid,
        check_colors,
        enter_specs,
    )

    for module in (check_colors, enter_specs, build_grid):
        register_handler(module.handler)


_register_defaults()
