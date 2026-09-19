from __future__ import annotations

from core.models import PartStep, StepRevision
from core.services.enter_specs_calc import try_compute_grid_pixels
from core.services.step_settings import merge_validated_data, unwrap_settings


class EnterSpecsCompleteHandler:
    step_code = "ENTER_SPECS"

    def on_complete(
        self,
        *,
        part_step: PartStep,
        revision: StepRevision,
        user=None,
    ) -> dict | None:
        settings_data, _meta = unwrap_settings(revision.settings)
        grid = settings_data.get("grid_pixels") or try_compute_grid_pixels(settings_data)
        if not grid or not grid.get("width") or not grid.get("height"):
            return None

        return {
            "step_code": "BUILD_GRID",
            "settings": merge_validated_data(
                {
                    "grid": grid,
                    "conversion": {
                        "from_step": self.step_code,
                        "from_revision_id": str(revision.id),
                        "needle_density": settings_data.get("needle_density"),
                        "cos_number": settings_data.get("cos_number"),
                        "course_per_pixel": settings_data.get("course_per_pixel"),
                    },
                },
                source="propagated",
                from_step_code=self.step_code,
                from_revision_id=str(revision.id),
            ),
        }


handler = EnterSpecsCompleteHandler()
