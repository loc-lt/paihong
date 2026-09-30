from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import UUID_PATH_PARAM
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    SystemColorWriteSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceUpdateSerializer,
)

list_colors_document = {
    "summary": "List system colors (read-only) and the current user's custom colors.",
    "responses": {200: MergedColorSerializer(many=True)},
}

create_user_color_document = {
    "summary": "Create a custom user color.",
    "description": (
        "Requires code and hex_value. "
        "code must be unique among this user's custom colors. "
        "hex_value must be unique among this user's custom colors and all system colors. "
        "System colors are managed via /system_colors (Admin/Developer only)."
    ),
    "request": UserColorPreferenceCreateSerializer,
    "responses": {201: MergedColorSerializer},
}

update_user_color_document = {
    "summary": "Update a custom user color.",
    "description": (
        "PATCH code, hex_value, name, and/or display_order. "
        "Id must be a custom color id from GET /colors. "
        "System colors cannot be changed."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": UserColorPreferenceUpdateSerializer,
    "responses": {200: MergedColorSerializer},
}

delete_user_color_document = {
    "summary": "Delete a custom user color.",
    "description": "System colors cannot be deleted.",
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

create_system_color_document = {
    "summary": "Create a system color (Admin/Developer only).",
    "description": (
        "Requires code, hex_value, name; display_order optional (default 0). "
        "code and hex_value must be unique among system colors."
    ),
    "request": SystemColorWriteSerializer,
    "responses": {201: ColorDefinitionSerializer},
}

update_system_color_document = {
    "summary": "Update a system color (Admin/Developer only).",
    "description": (
        "PATCH code, hex_value, name, and/or display_order. "
        "code and hex_value must stay unique among system colors."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": SystemColorWriteSerializer,
    "responses": {200: ColorDefinitionSerializer},
}

delete_system_color_document = {
    "summary": "Delete a system color (Admin/Developer only).",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: OpenApiResponse(description="Deleted")},
}
