from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse

from core.openapi_params import UUID_PATH_PARAM
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    SystemColorWriteSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceUpdateSerializer,
)

_COLOR_GROUP_QUERY = [
    OpenApiParameter(
        "is_svg",
        OpenApiTypes.BOOL,
        OpenApiParameter.QUERY,
        required=False,
        description=(
            "SVG palette, used from the start of the workflow through BUILD_GRID. "
            "true returns the 8 SVG system colors plus the user's SVG custom colors."
        ),
    ),
    OpenApiParameter(
        "is_pixel",
        OpenApiTypes.BOOL,
        OpenApiParameter.QUERY,
        required=False,
        description=(
            "Pixel palette, used in START_DESIGNING. "
            "true returns every pixel system color plus the user's pixel custom colors."
        ),
    ),
]

list_colors_document = {
    "summary": "List system colors (read-only) and the current user's custom colors.",
    "description": (
        "Filter with `is_svg` and/or `is_pixel`. "
        "Steps through BUILD_GRID use `is_svg=true`. "
        "START_DESIGNING uses `is_pixel=true`. "
        "An invalid value returns an empty list."
    ),
    "parameters": _COLOR_GROUP_QUERY,
    "responses": {200: MergedColorSerializer(many=True)},
}

create_user_color_document = {
    "summary": "Create a custom user color.",
    "description": (
        "Requires code, hex_value, is_svg, and is_pixel. "
        "SVG custom colors are is_svg=true and is_pixel=false. "
        "Pixel custom colors are is_svg=false and is_pixel=true. "
        "code and hex_value must be unique inside that group."
    ),
    "request": UserColorPreferenceCreateSerializer,
    "responses": {201: MergedColorSerializer},
}

update_user_color_document = {
    "summary": "Update a custom user color.",
    "description": (
        "PATCH code, hex_value, name, display_order, is_svg, and/or is_pixel. "
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
    "description": (
        "Filter with `is_svg` and/or `is_pixel`. "
        "`is_svg=true` is the 8 SVG colors. "
        "`is_pixel=true` is all 16 pixel colors. "
        "An invalid value returns an empty list."
    ),
    "parameters": _COLOR_GROUP_QUERY,
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
        "Requires code, hex_value, name, is_svg, and is_pixel. "
        "display_order is optional (default 0). "
        "A system color may belong to both groups. "
        "code and hex_value must be unique among system colors."
    ),
    "request": SystemColorWriteSerializer,
    "responses": {201: ColorDefinitionSerializer},
}

update_system_color_document = {
    "summary": "Update a system color (Admin/Developer only).",
    "description": (
        "PATCH code, hex_value, name, display_order, is_svg, and/or is_pixel. "
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
