from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiRequest,
    OpenApiResponse,
    extend_schema_serializer,
)
from rest_framework import serializers

from core.openapi_params import SOURCE_ID_PATH_PARAM, UUID_PATH_PARAM
from core.serializers.part_serializers import (
    BulkCreatePartSerializer,
    BulkDeletePartSerializer,
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)

class DesigningPartListPaginationSerializer(serializers.Serializer):
    total_items = serializers.IntegerField()
    page_size = serializers.IntegerField()
    current_page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    next_page = serializers.CharField(allow_null=True)
    previous_page = serializers.CharField(allow_null=True)


@extend_schema_serializer(many=False)
class DesigningPartListResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    data = PartSerializer(many=True)
    pagination = DesigningPartListPaginationSerializer()


list_designing_parts_document = {
    "summary": "List parts that have reached START_DESIGNING.",
    "description": (
        "Parts across every work item whose BUILD_GRID step is done, so "
        "START_DESIGNING is available. `q` matches part name "
        "(case-insensitive). `created_from` and `created_to` are inclusive "
        "dates (`YYYY-MM-DD`) on the part created date. An invalid date "
        "returns an empty page. `page` starts at 1. `page_size` defaults to 5 "
        "and cannot exceed 100."
    ),
    "parameters": [
        OpenApiParameter(
            "q",
            OpenApiTypes.STR,
            OpenApiParameter.QUERY,
            required=False,
            description="Case-insensitive match on part name.",
        ),
        OpenApiParameter(
            "created_from",
            OpenApiTypes.DATE,
            OpenApiParameter.QUERY,
            required=False,
            description="Inclusive start of the part created date (YYYY-MM-DD).",
        ),
        OpenApiParameter(
            "created_to",
            OpenApiTypes.DATE,
            OpenApiParameter.QUERY,
            required=False,
            description="Inclusive end of the part created date (YYYY-MM-DD).",
        ),
        OpenApiParameter(
            "page",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            required=False,
            description="Page number, starting at 1.",
        ),
        OpenApiParameter(
            "page_size",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            required=False,
            description="Items per page. Default 5, maximum 100.",
        ),
    ],
    "responses": {200: DesigningPartListResponseSerializer},
}

create_part_document = {
    "summary": "Create one or more parts for a source document.",
    "description": (
        "multipart/form-data. `source_document_id` once. Repeat `previews` once per "
        "part (required). Names are assigned `New part 1`, `New part 2`, … continuing "
        "after parts that already exist on the source document. Sequences continue "
        "from the highest sequence. Each part initializes workflow steps like PDF "
        "import (RECEIVE_FILES auto-completed, PICK_UPPER waits for the user)."
    ),
    "request": BulkCreatePartSerializer,
    "responses": {201: PartDetailSerializer(many=True)},
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
    "summary": "Delete one or more parts.",
    "description": (
        "JSON body `{\"ids\": [\"<uuid>\", ...]}`. Hard-deletes every listed part "
        "with its workflow steps, step revisions and step 10 design workspace. "
        "Stored files no longer used by anything else are removed. Unknown ids "
        "reject the whole request. Sequences of the remaining parts are not renumbered."
    ),
    "request": OpenApiRequest(
        request=BulkDeletePartSerializer,
        examples=[
            OpenApiExample(
                "Delete parts",
                value={"ids": ["00000000-0000-0000-0000-000000000000"]},
                request_only=True,
            )
        ],
    ),
    "responses": {200: OpenApiResponse(description="Deleted")},
}

list_source_document_parts_document = {
    "summary": "List parts for a source document.",
    "parameters": [SOURCE_ID_PATH_PARAM],
    "responses": {200: PartSerializer(many=True)},
}
