from drf_spectacular.utils import OpenApiResponse

from core.serializers.part_serializers import WorkItemPartsListSerializer
from core.serializers.work_item_process_serializers import (
    ProcessWorkItemResultSerializer,
    ProcessWorkItemSerializer,
)
from core.serializers.work_item_serializers import (
    UpdateWorkItemSerializer,
    WorkItemDetailSerializer,
    WorkItemItemCodeAvailabilitySerializer,
    WorkItemSerializer,
)

get_item_code_availability_document = {
    "summary": "Check item code availability before creating a work item.",
    "description": (
        "Returns whether the item code is available (not yet used). "
        "Match is case-insensitive."
    ),
    "responses": {200: WorkItemItemCodeAvailabilitySerializer},
}

get_work_items_document = {
    "summary": "List work items.",
    "description": (
        "Each work item includes parts_count, completed_parts, and a derived status "
        "(New / Designing / Completed / Failed) based on part progress."
    ),
    "responses": {200: WorkItemSerializer(many=True)},
}

create_work_item_document = {
    "summary": "Process work item (upload + AI detection + parts).",
    "description": (
        "Create a work item, upload one or more source files, run AI part detection "
        "(stub until AI service is connected), and initialize parts with "
        "RECEIVE_FILES marked as done (step 1 only). "
        "PICK_UPPER remains for the user to complete manually. "
        "Use multipart/form-data with fields: item_code (unique), name, status, "
        "workflow_template_id, and files[] (multiple files, same field name). "
        "Allowed source extensions: PDF, AI, DXF, DWG (max 50 MB each)."
    ),
    "request": ProcessWorkItemSerializer,
    "responses": {201: ProcessWorkItemResultSerializer},
}

get_work_item_document = {
    "summary": "Get work item detail.",
    "description": (
        "Returns work item with nested source_documents and parts. "
        "Each part includes total_steps and completed_steps (status = done)."
    ),
    "responses": {200: WorkItemDetailSerializer},
}

update_work_item_document = {
    "summary": "Update work item.",
    "request": UpdateWorkItemSerializer,
    "responses": {200: WorkItemSerializer},
}

delete_work_item_document = {
    "summary": "Delete work item.",
    "responses": {200: OpenApiResponse(description="Deleted")},
}

get_source_documents_document = {
    "summary": "List source documents.",
    "responses": {200: OpenApiResponse(description="Source documents list")},
}

get_work_item_parts_document = {
    "summary": "List parts for a work item.",
    "description": (
        "Returns all parts without pagination, plus total_parts and "
        "completed_parts (a part is completed when every step is done)."
    ),
    "responses": {200: WorkItemPartsListSerializer},
}
