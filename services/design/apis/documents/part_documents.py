from core.serializers.part_serializers import (
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)

get_part_document = {
    "summary": "Get part detail.",
    "responses": {200: PartDetailSerializer},
}

update_part_document = {
    "summary": "Update part.",
    "request": UpdatePartSerializer,
    "responses": {200: PartSerializer},
}
