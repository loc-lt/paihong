from drf_spectacular.utils import OpenApiResponse

from core.serializers.ai_design_serializers import (
    AiFilePathProductCodeSerializer,
    AiServiceResponseSerializer,
    CreateFileFcRequestSerializer,
    CreateFilePRequestSerializer,
    CreateFilesCRequestSerializer,
    CreateTrainDbAnchorRequestSerializer,
    CreateTrainDbRequestSerializer,
    MergeImagesRequestSerializer,
    SmartSRequestSerializer,
)

_AI_RESPONSES = {
    200: AiServiceResponseSerializer,
    400: OpenApiResponse(
        description=(
            "Validation or render failure. `message` starts with `[render_png][field]` "
            "or a field validation message."
        )
    ),
    500: OpenApiResponse(
        description="Unexpected backend error. `message` starts with `[backend]`."
    ),
    502: OpenApiResponse(
        description=(
            "Config, connect, or AI failure. `message` starts with `[config]`, "
            "`[ai_connect]`, or `[ai_response]`. `data` includes `stage`, `ai_url`, "
            "`ai_status`, `ai_body`, and `request_payload` when available."
        )
    ),
    504: OpenApiResponse(
        description="AI timed out. `message` starts with `[ai_timeout]`."
    ),
}

_ID_TO_PNG = (
    "Each revision id is a START_DESIGNING design-file revision. The backend reads "
    "that revision's gzip snapshot, renders a PNG, and sends the public media URL "
    "(`BE_DOMAIN` + `/media/...`, for example "
    "`http://192.168.160.95:82/media/objects/...png`) to the AI service. "
    "A successful AI JSON body is returned as-is. Failures are wrapped as "
    "`{status:false, message:'[stage] …', data:{stage,…}}` so the failing step "
    "is explicit."
)

_PASSTHROUGH_PATH = (
    "FE sends the image/SVG path in `file_path` directly. The backend forwards the "
    "validated body to the AI service unchanged."
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

split_regions_document = {
    "tags": ["AI design files"],
    "summary": "Split regions",
    "description": f"Recall `AI_DOMAIN/split_regions`. {_PASSTHROUGH_PATH}",
    "request": AiFilePathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

rotate_svg_document = {
    "tags": ["AI design files"],
    "summary": "Rotate SVG",
    "description": f"Recall `AI_DOMAIN/rotate_svg`. {_PASSTHROUGH_PATH}",
    "request": AiFilePathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

delete_paths_document = {
    "tags": ["AI design files"],
    "summary": "Delete paths",
    "description": f"Recall `AI_DOMAIN/delete_paths`. {_PASSTHROUGH_PATH}",
    "request": AiFilePathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

delete_anchors_document = {
    "tags": ["AI design files"],
    "summary": "Delete anchors",
    "description": f"Recall `AI_DOMAIN/delete_anchors`. {_PASSTHROUGH_PATH}",
    "request": AiFilePathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

color_paths_document = {
    "tags": ["AI design files"],
    "summary": "Color paths",
    "description": f"Recall `AI_DOMAIN/color_paths`. {_PASSTHROUGH_PATH}",
    "request": AiFilePathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

create_train_db_document = {
    "tags": ["AI design files"],
    "summary": "Create train DB",
    "description": (
        "Recall `AI_DOMAIN/create_train_db`. FE sends `file_path`, `index_list` "
        "(path indices), and `type` directly. The backend forwards the body unchanged."
    ),
    "request": CreateTrainDbRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_train_db_anchor_document = {
    "tags": ["AI design files"],
    "summary": "Create train DB anchors",
    "description": (
        "Recall `AI_DOMAIN/create_train_db_anchor`. FE sends `file_path` and "
        "`index_list` as pairs `[path_index, point_index]`. The backend forwards "
        "the body unchanged."
    ),
    "request": CreateTrainDbAnchorRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_file_fc_document = {
    "tags": ["AI design files"],
    "summary": "Create file FC / finalize P",
    "description": (
        "Recall `AI_DOMAIN/api/create_file_fc`. FE sends `image_id` instead of "
        "`image_path`. `type_machine` is optional. "
        + _ID_TO_PNG
    ),
    "request": CreateFileFcRequestSerializer,
    "responses": _AI_RESPONSES,
}
