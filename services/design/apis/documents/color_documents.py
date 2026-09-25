from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import UUID_PATH_PARAM
from core.openapi_params import UUID_PATH_PARAM
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceSerializer,
    UserColorPreferenceUpdateSerializer,
)

list_colors_document = {
    "summary": "List merged system and user colors.",
    "responses": {200: MergedColorSerializer(many=True)},
}

create_user_color_document = {
    "summary": "Create or override a user color preference.",
    "description": (
        "Custom color: send custom_hex (+ optional custom_name, display_order). "
        "System override: send color_definition_id (+ optional custom_hex/custom_name). "
        "display_order is ignored for system-linked colors."
    ),
    "request": UserColorPreferenceCreateSerializer,
    "responses": {201: MergedColorSerializer},
}

update_user_color_document = {
    "summary": "Update a user color preference.",
    "description": (
        "PATCH custom colors: custom_name, custom_hex, display_order. "
        "PATCH system override: custom_name, custom_hex only (order is fixed). "
        "Id must be a UserColorPreference id from GET /colors (not a bare system color id)."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": UserColorPreferenceUpdateSerializer,
    "responses": {200: MergedColorSerializer},
}

delete_user_color_document = {
    "summary": "Delete a user color preference.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: OpenApiResponse(description="Deleted")},
}

list_system_colors_document = {
    "summary": "List system color palette.",
    "responses": {200: ColorDefinitionSerializer(many=True)},
}

get_system_color_document = {
    "summary": "Get system color detail.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: ColorDefinitionSerializer},
}
