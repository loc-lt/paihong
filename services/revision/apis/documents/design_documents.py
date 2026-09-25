from core.openapi_params import TILE_VIEWPORT_QUERY_PARAMS, UUID_PATH_PARAM
from core.serializers.design_serializers import (
    DesignFileRevisionDetailSerializer,
    DesignFileTilesPatchSerializer,
    DesignFileTilesResponseSerializer,
    DesignFileRevisionSaveSerializer,
    DesignWorkspaceSerializer,
)

get_design_workspace_document = {
    "summary": "Get design workspace for START_DESIGNING.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: DesignWorkspaceSerializer},
}

get_design_file_document = {
    "summary": "Get official design file revision summary.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: DesignFileRevisionDetailSerializer},
}

design_file_autosave_document = {
    "summary": "Autosave design file revision.",
    "description": (
        "Creates a new DesignFileRevision row for layer-panel metadata (`layers[]`). "
        "Cell paint data is uploaded separately via PATCH "
        "/design_file_revisions/{id}/tiles (in-place on the same revision row)."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": DesignFileRevisionSaveSerializer,
    "responses": {201: DesignFileRevisionDetailSerializer},
}

design_file_save_document = {
    "summary": "Manual save design file revision.",
    "description": "Same body as autosave; revision_type = manual save.",
    "parameters": [UUID_PATH_PARAM],
    "request": DesignFileRevisionSaveSerializer,
    "responses": {201: DesignFileRevisionDetailSerializer},
}

design_file_complete_document = {
    "summary": "Complete design file — merge tiles and mark progress.",
    "description": (
        "Requires all prior files in DESIGN_FILE_SEQUENCE to be completed first "
        "(e.g. complete S1 before C). Opening/editing files is not blocked — only "
        "this complete action enforces order."
    ),
    "parameters": [UUID_PATH_PARAM],
    "responses": {201: DesignFileRevisionDetailSerializer},
}

get_design_file_tiles_document = {
    "summary": "Load grid tiles for a viewport.",
    "description": (
        "Returns tiles intersecting the viewport rectangle `[x0, x1) × [y0, y1)` "
        "in grid pixel coordinates. Tile keys use format `tx_ty` where "
        "`tx = floor(x / tile_size)` and `ty = floor(y / tile_size)`."
    ),
    "parameters": [UUID_PATH_PARAM, *TILE_VIEWPORT_QUERY_PARAMS],
    "responses": {200: DesignFileTilesResponseSerializer},
}

patch_design_file_tiles_document = {
    "summary": "Batch-update grid tiles on a design file revision.",
    "description": (
        "Updates snapshot tiles in-place and regenerates `preview_file` "
        "(PNG thumbnail of the current grid)."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": DesignFileTilesPatchSerializer,
    "responses": {200: DesignFileRevisionDetailSerializer},
}

restore_design_file_revision_document = {
    "summary": "Restore a design file revision.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {201: DesignFileRevisionDetailSerializer},
}
