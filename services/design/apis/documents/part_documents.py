from core.openapi_params import SOURCE_ID_PATH_PARAM, UUID_PATH_PARAM
from core.serializers.part_serializers import (
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)

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

list_source_document_parts_document = {
    "summary": "List parts for a source document.",
    "parameters": [SOURCE_ID_PATH_PARAM],
    "responses": {200: PartSerializer(many=True)},
}
