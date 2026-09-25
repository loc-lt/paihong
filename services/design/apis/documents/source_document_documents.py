from drf_spectacular.utils import OpenApiResponse

from core.openapi_params import UUID_PATH_PARAM
from core.serializers.source_document_serializers import SourceDocumentSerializer

get_source_document_document = {
    "summary": "Get source document detail.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: SourceDocumentSerializer},
}

delete_source_document_document = {
    "summary": "Delete source document.",
    "parameters": [UUID_PATH_PARAM],
    "responses": {200: OpenApiResponse(description="Deleted")},
}
