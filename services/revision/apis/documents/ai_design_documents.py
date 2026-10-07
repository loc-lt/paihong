from drf_spectacular.utils import OpenApiResponse

from core.serializers.ai_design_serializers import (
    AiServiceResponseSerializer,
    CreateFilePRequestSerializer,
    CreateFilesCRequestSerializer,
    MergeImagesRequestSerializer,
    SmartSRequestSerializer,
)

_AI_RESPONSES = {
    200: AiServiceResponseSerializer,
    404: AiServiceResponseSerializer,
    422: OpenApiResponse(
        description="Validation error from the AI service. Body is forwarded unchanged."
    ),
    500: OpenApiResponse(
        description="Error from the AI service. JSON or plain text is forwarded unchanged."
    ),
    502: OpenApiResponse(description="AI service is not configured or unreachable."),
    504: OpenApiResponse(description="AI service timed out."),
}

_ID_TO_PNG = (
    "Each revision id is a START_DESIGNING design-file revision. The backend reads "
    "that revision's gzip snapshot, renders a PNG, and sends the saved PNG path to "
    "the AI service. The AI status code and response body are returned unchanged."
)

smart_s_document = {
    "tags": ["AI design files"],
    "summary": "Smart S",
    "description": (
        "Recall `AI_DOMAIN/api/smart_s`. FE sends `svg_id` instead of `path_svg`. "
        + _ID_TO_PNG
    ),
    "request": SmartSRequestSerializer,
    "responses": _AI_RESPONSES,
}

merge_images_document = {
    "tags": ["AI design files"],
    "summary": "Merge Images",
    "description": (
        "Recall `AI_DOMAIN/api/merge_images`. FE sends `image_ids` instead of "
        "`image_paths`. The first id is the bottom layer and the last id is the top. "
        "Where images overlap, the topmost non-background pixel wins. "
        "`background` is `white` or `black` (default `white`). "
        + _ID_TO_PNG
    ),
    "request": MergeImagesRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_files_c_document = {
    "tags": ["AI design files"],
    "summary": "Create files C",
    "description": (
        "Recall `AI_DOMAIN/api/create_files_c`. FE sends `file_id` instead of "
        "`file_path`. The AI service detects the L/R side and writes four files "
        "`image_<product_code>_{L,R}.png` plus the 180-degree copies (`_F`). "
        + _ID_TO_PNG
    ),
    "request": CreateFilesCRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_file_p_document = {
    "tags": ["AI design files"],
    "summary": "Create file P",
    "description": (
        "Recall `AI_DOMAIN/api/create_file_p`. FE sends `l_id`, `r_id`, `l_f_id`, "
        "and `r_f_id` instead of `path_l`, `path_r`, `path_l_f`, and `path_r_f`. "
        "`wales_per_inch`, `courses_per_cm`, and `courses_per_pixel` are optional. "
        + _ID_TO_PNG
    ),
    "request": CreateFilePRequestSerializer,
    "responses": _AI_RESPONSES,
}
