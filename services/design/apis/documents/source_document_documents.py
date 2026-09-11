from drf_spectacular.utils import OpenApiResponse

from core.serializers.source_document_serializers import SourceDocumentSerializer

get_source_document_document = {
    "summary": "Get source document detail.",
    "responses": {200: SourceDocumentSerializer},
}

delete_source_document_document = {
    "summary": "Delete source document.",
    "responses": {200: OpenApiResponse(description="Deleted")},
}
