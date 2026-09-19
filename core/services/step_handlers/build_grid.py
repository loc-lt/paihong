from __future__ import annotations

from core.models import PartStep, StepRevision
from core.services.design_grid.snapshot import create_empty_grid_snapshot
from core.services.design_workspace import initialize_design_workspace
from core.services.step_settings import merge_validated_data, unwrap_settings


class BuildGridCompleteHandler:
    step_code = "BUILD_GRID"

    def on_complete(
        self,
        *,
        part_step: PartStep,
        revision: StepRevision,
        user=None,
    ) -> dict | None:
        settings_data, _meta = unwrap_settings(revision.settings)
        grid = settings_data.get("grid") or settings_data.get("grid_pixels") or {}
        width = int(grid.get("width") or 0)
        height = int(grid.get("height") or 0)
        if width <= 0 or height <= 0:
            return None

        snapshot_file = create_empty_grid_snapshot(
            width=width,
            height=height,
            created_by=user,
        )
        enriched = {
            **settings_data,
            "grid": {"width": width, "height": height},
            "grid_snapshot_id": str(snapshot_file.id),
        }
        revision.settings = merge_validated_data(
            enriched,
            source=_meta.get("source", "manual"),
            from_step_code=_meta.get("from_step_code", ""),
            from_revision_id=_meta.get("from_revision_id", ""),
        )
        from core.services.step_revision import _settings_hash

        revision.settings_hash = _settings_hash(revision.settings)
        revision.save(update_fields=["settings", "settings_hash", "modified"])

        designing_step = part_step.part.steps.select_related("step").filter(
            step__code="START_DESIGNING"
        ).first()
        if not designing_step:
            return None

        initialize_design_workspace(
            part_step=designing_step,
            grid_width=width,
            grid_height=height,
            snapshot_file=snapshot_file,
            user=user,
        )

        return {
            "step_code": "START_DESIGNING",
            "settings": merge_validated_data(
                {"active_file_type": "S1", "progress": {}},
                source="grid_import",
                from_step_code=self.step_code,
                from_revision_id=str(revision.id),
            ),
        }


handler = BuildGridCompleteHandler()
