from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import TILE_VIEWPORT_QUERY_PARAMS, UUID_PATH_PARAM
from core.serializers.design_serializers import (
    CreateDraftDesignFileSerializer,
    RenameDraftDesignFileSerializer,
    DesignFileRevisionDetailSerializer,
    DesignFileSerializer,
    DesignFileTilesPatchSerializer,
    DesignFileTilesResponseSerializer,
    InitializeDesignFileRevisionSerializer,
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
        "JSON body requires `name`, `width`, and `height`. Creates an empty grid file "
        "(`file_type` `D1`, `D2`, …) and revision 1 with a gzip snapshot of that canvas "
        "so GET tiles can be called immediately. Paint with PATCH tiles and save layers "
        "the same way as file S. Saving or completing a draft does not check earlier "
        "main files and does not change main-file progress."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": CreateDraftDesignFileSerializer,
    "responses": {201: DesignFileSerializer},
}

reopen_design_file_document = {
    "summary": "Reopen a completed main design file for editing.",
    "description": (
        "For a completed file in S–F (for example S1). Sets progress of that file and "
        "every later file that is already complete back to `in_progress`, clears "
        "`official_revision` on those files, and sets `active_file_type` to the reopened "
        "file. If START_DESIGNING was done, the step returns to in progress. Draft files "
        "cannot be reopened. Existing revisions stay; the latest revision remains."
    ),
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: DesignWorkspaceSerializer},
}

rename_draft_design_file_document = {
    "summary": "Rename a draft file.",
    "description": (
        "JSON body requires `name`. Only draft files (`D1`, `D2`, …) can be renamed. "
        "Main files S–F keep their generated display name."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": RenameDraftDesignFileSerializer,
    "responses": {200: DesignFileSerializer},
}

delete_draft_design_file_document = {
    "summary": "Delete a draft file.",
    "description": (
        "Deletes the draft and all of its revisions. Main files S–F cannot be deleted. "
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
        "Marks the latest revision official. For main files S–F, updates workspace "
        "progress and requires prior files to be done (e.g. complete S1 before C). "
        "Completing a main file also creates an empty-tile revision on the next file in "
        "S → S1 → C → H → P → FC → F at the same grid size, and sets that next "
        "file to `in_progress` when it was `not_started`. If the next file already has "
        "a revision, that empty revision is not created. "
        "F has no next file. Completing F marks START_DESIGNING done. Draft files (`D1`, `D2`, …) skip that order check, do "
        "not change main-file progress, and do not create a following revision. "
        "Does not merge tiles or read `tile_manifest`."
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

initialize_design_file_revision_document = {
    "summary": "Create the first revision of a design file with grid tiles.",
    "description": (
        "Use this when the file has no revision yet, so there is no "
        "`design_file_revisions` id to PATCH. Body matches PATCH tiles: "
        "`grid_width`, `grid_height`, and `tiles` (`key` + base64 `data`). "
        "Creates revision 1, stores the tiles unchanged, and marks a main file "
        "`in_progress` when it was `not_started`. "
        "If the file already has a revision, returns 400 with that revision id — "
        "PATCH `/design_file_revisions/{id}/tiles` instead. "
        "Does not decompress tiles and does not draw a preview."
    ),
    "parameters": [UUID_PATH_PARAM],
    "request": InitializeDesignFileRevisionSerializer,
    "responses": {201: DesignFileRevisionDetailSerializer},
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
