from __future__ import annotations

from core.models import PartStep, StepRevision
from core.services.check_colors_ai import derive_canvas_frame_settings
from core.services.step_settings import merge_validated_data, unwrap_settings


class CheckColorsCompleteHandler:
    step_code = "CHECK_COLORS"

    def on_complete(
        self,
        *,
        part_step: PartStep,
        revision: StepRevision,
        user=None,
    ) -> dict | None:
        settings_data, _meta = unwrap_settings(revision.settings)
        canvas_settings = derive_canvas_frame_settings(
            check_colors_settings=settings_data,
            revision=revision,
        )
        return {
            "step_code": "CANVAS_FRAME_MEASURE",
            "settings": merge_validated_data(
                canvas_settings,
                source="ai",
                from_step_code=self.step_code,
                from_revision_id=str(revision.id),
            ),
        }


handler = CheckColorsCompleteHandler()
