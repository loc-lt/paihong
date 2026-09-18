from drf_spectacular.utils import OpenApiResponse

from core.serializers.revision_serializers import (
    PartStepDetailSerializer,
    PartStepSerializer,
    PartStepsListSerializer,
    RestoreRevisionSerializer,
    SaveStepRevisionSerializer,
    StepRevisionDetailSerializer,
)

_SAVE_REVISION_DESCRIPTION = (
    "Save step data. Use multipart/form-data when uploading files.\n\n"
    "- **settings**: JSON object (or JSON string in multipart), step-specific fields\n"
    "- **files**: one or more image/output files (PNG, JPG, JPEG, SVG, PDF, …)\n"
    "- **base_revision_id** (optional): latest revision ID for conflict detection\n"
    "- **note** (optional): save note"
)

get_part_steps_document = {
    "summary": "List part steps.",
    "description": "Returns all steps plus total_steps and completed_steps (status = done).",
    "responses": {200: PartStepsListSerializer},
}

sync_part_steps_document = {
    "summary": "Sync part steps from workflow template.",
    "responses": {200: PartStepSerializer(many=True)},
}

get_part_step_document = {
    "summary": "Get part step detail.",
    "responses": {200: PartStepDetailSerializer},
}

get_revisions_document = {
    "summary": "List step revisions.",
    "responses": {200: StepRevisionDetailSerializer(many=True)},
}

autosave_revision_document = {
    "summary": "Create autosave revision.",
    "description": _SAVE_REVISION_DESCRIPTION,
    "request": SaveStepRevisionSerializer,
    "responses": {201: StepRevisionDetailSerializer},
}

manual_save_revision_document = {
    "summary": "Create manual save revision.",
    "description": _SAVE_REVISION_DESCRIPTION,
    "request": SaveStepRevisionSerializer,
    "responses": {201: StepRevisionDetailSerializer},
}

official_save_revision_document = {
    "summary": "Complete step with official revision.",
    "description": (
        _SAVE_REVISION_DESCRIPTION
        + "\n\nA step can be completed again even if already done. "
        "Each complete creates a new official revision and hard-deletes all "
        "revisions for later steps (e.g. re-complete step 2 clears steps 3, 4, 5)."
    ),
    "request": SaveStepRevisionSerializer,
    "responses": {201: StepRevisionDetailSerializer},
}

get_revision_document = {
    "summary": "Get revision detail.",
    "responses": {200: StepRevisionDetailSerializer},
}

restore_revision_document = {
    "summary": "Restore revision.",
    "request": RestoreRevisionSerializer,
    "responses": {201: StepRevisionDetailSerializer},
}
