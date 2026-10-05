from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import TILE_VIEWPORT_QUERY_PARAMS, UUID_PATH_PARAM
from core.serializers.design_serializers import (
    CreateDraftDesignFileSerializer,
    DesignFileRevisionDetailSerializer,
    DesignFileSerializer,
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

create_draft_design_file_document = {
    "summary": "Add a draft file to the design workspace.",
    "description": (
        "JSON body: optional `name` (default `Draft {n}`). Creates an empty grid file "
        "(`file_type` `D1`, `D2`, …) with revision 1, same canvas size as "
        "`workspace.settings.grid`. Paint with PATCH tiles and save layers the same way "
        "as file S. Saving or completing a draft does not check earlier main files and "
        "does not change main-file progress."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": CreateDraftDesignFileSerializer,
    "responses": {201: DesignFileSerializer},
}

delete_draft_design_file_document = {
    "summary": "Delete a draft file.",
    "description": (
        "Deletes the draft and all of its revisions. Main files S–KMO cannot be deleted. "
        "Path `file_type` is the draft code (`D1`, `D2`, …)."
    ),
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: OpenApiResponse(description="Deleted")},
}

design_file_autosave_document = {
    "summary": "Autosave design file revision.",
    "description": (
        "Creates a new DesignFileRevision row for layer-panel metadata (`layers[]`). "
        "Reuses the previous snapshot and preview. Does not read `tile_manifest` and "
        "does not repaint the grid. Cell paint data is uploaded separately via PATCH "
        "/design_file_revisions/{id}/tiles. Draft files (`D1`, `D2`, …) use the same "
        "layers and tiles APIs. Draft saves do not require earlier main files to be complete."
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
    "summary": "Complete design file and mark progress.",
    "description": (
        "Marks the latest revision official. For main files S–KMO, updates workspace "
        "progress and requires prior files to be done (e.g. complete S1 before C). "
        "Draft files (`D1`, `D2`, …) skip that order check and do not change main-file "
        "progress. Does not merge tiles, read `tile_manifest`, or repaint `preview_file`."
    ),
    "parameters": [UUID_PATH_PARAM],
    "responses": {201: DesignFileRevisionDetailSerializer},
}

get_design_file_tiles_document = {
    "summary": "Load grid tiles for a viewport.",
    "description": (
        "Returns tiles intersecting the viewport rectangle `[x0, x1) × [y0, y1)` "
        "in grid pixel coordinates. Each value is the same `data` string stored by PATCH. "
        "Tile keys use format `tx_ty` where "
        "`tx = floor(x / tile_size)` and `ty = floor(y / tile_size)`."
    ),
    "parameters": [UUID_PATH_PARAM, *TILE_VIEWPORT_QUERY_PARAMS],
    "responses": {200: DesignFileTilesResponseSerializer},
}

patch_design_file_tiles_document = {
    "summary": "Batch-update grid tiles on a design file revision.",
    "description": (
        "Stores each tile `data` string unchanged (base64 of gzip JSON, or base64 of JSON). "
        "Does not decompress tiles, does not write `tile_manifest`, and does not "
        "regenerate `preview_file`. "
        "Optional `grid_width` + `grid_height` resize this revision: all existing "
        "tiles are dropped and replaced by the tiles in this request (later PATCHes "
        "with the same size merge as usual). BUILD_GRID only sets the size of the "
        "first S revision. A tile key outside the grid is rejected (400)."
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
