from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

UUID_PATH_PARAM = OpenApiParameter(
    "id",
    OpenApiTypes.UUID,
    OpenApiParameter.PATH,
    description="Resource UUID.",
)

SOURCE_ID_PATH_PARAM = OpenApiParameter(
    "source_id",
    OpenApiTypes.UUID,
    OpenApiParameter.PATH,
    description="Source document UUID.",
)

ITEM_CODE_PATH_PARAM = OpenApiParameter(
    "item_code",
    OpenApiTypes.STR,
    OpenApiParameter.PATH,
    description="Work item code.",
)

TILE_VIEWPORT_QUERY_PARAMS = [
    OpenApiParameter(
        "x0",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Left column of the viewport in grid pixel space (inclusive).",
        default=0,
    ),
    OpenApiParameter(
        "y0",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description="Top row of the viewport in grid pixel space (inclusive).",
        default=0,
    ),
    OpenApiParameter(
        "x1",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description=(
            "Right column of the viewport in grid pixel space (exclusive). "
            "Defaults to revision grid_width when omitted."
        ),
        required=False,
    ),
    OpenApiParameter(
        "y1",
        OpenApiTypes.INT,
        OpenApiParameter.QUERY,
        description=(
            "Bottom row of the viewport in grid pixel space (exclusive). "
            "Defaults to revision grid_height when omitted."
        ),
        required=False,
    ),
]
