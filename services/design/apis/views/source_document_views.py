from drf_spectacular.utils import extend_schema

from rest_framework import viewsets



from core.models import SourceDocument

from core.responses import success_response

from core.serializers.source_document_serializers import SourceDocumentSerializer

from core.utils import get_instance



from ..documents.source_document_documents import (

    delete_source_document_document,

    get_source_document_document,

)





class SourceDocumentViewSet(viewsets.ViewSet):

    @extend_schema(**get_source_document_document)

    def retrieve(self, request, pk=None):
        source_document = get_instance(SourceDocument, pk)
        source_document = SourceDocument.objects.select_related(
            "file",
            "work_item",
        ).get(pk=source_document.pk)
        return success_response(
            SourceDocumentSerializer(source_document).data,
            "Source document retrieved successfully!",
        )



    @extend_schema(**delete_source_document_document)

    def destroy(self, request, pk=None):

        source_document = get_instance(SourceDocument, pk)

        source_document.delete()

        return success_response(None, "Source document deleted successfully!")

