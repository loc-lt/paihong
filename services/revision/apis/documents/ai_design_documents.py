from drf_spectacular.utils import OpenApiResponse

from core.serializers.ai_design_serializers import (
    AiServiceResponseSerializer,
    AiUrlPathProductCodeSerializer,
    AiUrlSvgProductCodeSerializer,
    AutoJobRequestSerializer,
    CombineFcRequestSerializer,
    CreateFileFcRequestSerializer,
    CreateFilePRequestSerializer,
    CreateFilesCRequestSerializer,
    CreateKmoRequestSerializer,
    CreateTrainDbAnchorRequestSerializer,
    CreateTrainDbRequestSerializer,
    MergeImagesRequestSerializer,
    ShiftOddRowsRequestSerializer,
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

_PASSTHROUGH_SVG = (
    "FE sends `url_svg` and `product_code` directly. The backend forwards the "
    "validated body to the AI service unchanged."
)

smart_s_document = {
    "tags": ["ai_design_files"],
    "summary": "Smart S",
    "description": (
        "Recall `AI_DOMAIN/api/v1/smart_s`. FE sends `svg_id`. The backend sends "
        "`url_svg` as the public PNG URL. "
        + _ID_TO_PNG
    ),
    "request": SmartSRequestSerializer,
    "responses": _AI_RESPONSES,
}

merge_images_document = {
    "tags": ["ai_design_files"],
    "summary": "Merge Images",
    "description": (
        "Recall `AI_DOMAIN/api/v1/merge_images`. FE sends `list_image_ids`. The "
        "backend sends `list_url_images`. The first id is the bottom layer and the "
        "last id is the top. Where images overlap, the topmost non-background pixel "
        "wins. `background` is `white` or `black` (default `white`). "
        + _ID_TO_PNG
    ),
    "request": MergeImagesRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_files_c_document = {
    "tags": ["ai_design_files"],
    "summary": "Create files C",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_files_c`. FE sends `image_id`. The backend "
        "sends `url_image`. The AI service detects the L/R side and writes four files "
        "`image_<product_code>_{L,R}.png` plus the 180-degree copies (`_F`). "
        + _ID_TO_PNG
    ),
    "request": CreateFilesCRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_file_p_document = {
    "tags": ["ai_design_files"],
    "summary": "Create file P",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_file_p`. FE sends `l_id`, `r_id`, `l_f_id`, "
        "and `r_f_id`. The backend sends `url_l`, `url_r`, `url_l_f`, and `url_r_f`. "
        "`wales_per_inch`, `courses_per_cm`, and `courses_per_pixel` are optional. "
        + _ID_TO_PNG
    ),
    "request": CreateFilePRequestSerializer,
    "responses": _AI_RESPONSES,
}

split_regions_document = {
    "tags": ["ai_design_files"],
    "summary": "Split regions",
    "description": (
        "Recall `AI_DOMAIN/api/v1/split_regions`. FE sends `url_path` and "
        "`product_code`. The backend forwards the validated body unchanged."
    ),
    "request": AiUrlPathProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

rotate_svg_document = {
    "tags": ["ai_design_files"],
    "summary": "Rotate SVG",
    "description": f"Recall `AI_DOMAIN/api/v1/rotate_svg`. {_PASSTHROUGH_SVG}",
    "request": AiUrlSvgProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

delete_paths_document = {
    "tags": ["ai_design_files"],
    "summary": "Delete paths",
    "description": f"Recall `AI_DOMAIN/api/v1/delete_paths`. {_PASSTHROUGH_SVG}",
    "request": AiUrlSvgProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

delete_anchors_document = {
    "tags": ["ai_design_files"],
    "summary": "Delete anchors",
    "description": f"Recall `AI_DOMAIN/api/v1/delete_anchors`. {_PASSTHROUGH_SVG}",
    "request": AiUrlSvgProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

color_paths_document = {
    "tags": ["ai_design_files"],
    "summary": "Color paths",
    "description": f"Recall `AI_DOMAIN/api/v1/color_paths`. {_PASSTHROUGH_SVG}",
    "request": AiUrlSvgProductCodeSerializer,
    "responses": _AI_RESPONSES,
}

create_train_db_document = {
    "tags": ["ai_design_files"],
    "summary": "Create train DB",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_train_db`. FE sends `url_svg`, `index_list` "
        "(path indices), and `type` directly. The backend forwards the body unchanged."
    ),
    "request": CreateTrainDbRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_train_db_anchor_document = {
    "tags": ["ai_design_files"],
    "summary": "Create train DB anchors",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_train_db_anchor`. FE sends `url_svg` and "
        "`index_list` as pairs `[path_index, point_index]`. The backend forwards "
        "the body unchanged."
    ),
    "request": CreateTrainDbAnchorRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_file_fc_document = {
    "tags": ["ai_design_files"],
    "summary": "Create file FC / finalize P",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_file_fc`. FE sends `image_id`. The backend "
        "sends `url_image`. `type_machine` is optional. "
        + _ID_TO_PNG
    ),
    "request": CreateFileFcRequestSerializer,
    "responses": _AI_RESPONSES,
}

auto_job_document = {
    "tags": ["ai_design_files"],
    "summary": "Auto job",
    "description": (
        "Recall `AI_DOMAIN/api/v1/auto_job`. FE sends `image_id`. The backend sends "
        "`url_image`. `type_machine` and `number_jackquard` are optional. "
        + _ID_TO_PNG
    ),
    "request": AutoJobRequestSerializer,
    "responses": _AI_RESPONSES,
}

combine_fc_document = {
    "tags": ["ai_design_files"],
    "summary": "Combine FC",
    "description": (
        "Recall `AI_DOMAIN/api/v1/combine_fc`. FE sends `ff_id` and `fb_id`. The "
        "backend sends `url_ff` and `url_fb`. `ff_has_hole` and `fb_has_hole` default "
        "to false. "
        + _ID_TO_PNG
    ),
    "request": CombineFcRequestSerializer,
    "responses": _AI_RESPONSES,
}

shift_odd_rows_document = {
    "tags": ["ai_design_files"],
    "summary": "Shift odd rows",
    "description": (
        "Recall `AI_DOMAIN/api/v1/shift_odd_rows`. FE sends `image_id` and `value`. "
        "The backend sends `url_image` and `value`. "
        + _ID_TO_PNG
    ),
    "request": ShiftOddRowsRequestSerializer,
    "responses": _AI_RESPONSES,
}

create_kmo_document = {
    "tags": ["ai_design_files"],
    "summary": "Create KMO",
    "description": (
        "Recall `AI_DOMAIN/api/v1/create_kmo`. FE sends `image_id`. The backend sends "
        "`url_image`. `name_machine`, `gauge`, `width`, `rt`, `product_code`, "
        "`course_per_pixel`, and `kmo_has_valve_chain` are optional. "
        + _ID_TO_PNG
    ),
    "request": CreateKmoRequestSerializer,
    "responses": _AI_RESPONSES,
}
