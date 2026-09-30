from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import SOURCE_ID_PATH_PARAM, UUID_PATH_PARAM
from core.serializers.part_serializers import (
    CreatePartSerializer,
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)

create_part_document = {
    "summary": "Create a part manually for a source document.",
    "description": (
        "multipart/form-data: `source_document_id`, `preview` (required), `name` "
        "(optional, default `Part {sequence}`). `sequence` is assigned as the next "
        "number within the source document. Workflow steps are initialized like PDF "
        "import (RECEIVE_FILES auto-completed, PICK_UPPER waits for the user)."
    ),
    "request": CreatePartSerializer,
    "responses": {201: PartDetailSerializer},
}

get_part_document = {
    "summary": "Get part detail.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: PartDetailSerializer},
}

update_part_document = {
    "summary": "Update part (name, status, preview image).",
    "description": (
        "JSON or multipart/form-data. Use field `preview` to replace the part "
        "thumbnail when PDF import detected the wrong region."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": UpdatePartSerializer,
    "responses": {200: PartSerializer},
}

delete_part_document = {
    "summary": "Delete a part.",
    "description": (
        "Hard-deletes the part with all workflow steps, step revisions and the "
        "step 10 design workspace. Stored files no longer used by anything else "
        "are removed. Sequences of the remaining parts are not renumbered."
    ),
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: OpenApiResponse(description="Deleted")},
}

list_source_document_parts_document = {
    "summary": "List parts for a source document.",
    "parameters": [SOURCE_ID_PATH_PARAM],
    "responses": {200: PartSerializer(many=True)},
}
