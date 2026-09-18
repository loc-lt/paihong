from drf_spectacular.utils import extend_schema
from rest_framework import viewsets

from core.filters import PartFilter
from core.models import Part, SourceDocument
from core.paginators import CustomPaginator
from core.responses import success_response
from core.serializers.part_serializers import (
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)
from core.utils import get_instance, global_response_errors

from ..documents.part_documents import get_part_document, update_part_document


class PartViewSet(viewsets.ViewSet):
    @extend_schema(**get_part_document)
    def retrieve(self, request, pk=None):
        part = get_instance(Part, pk)
        part = Part.objects.select_related(
            "preview_file",
            "source_document__file",
            "source_document__svg_file",
        ).get(pk=part.pk)
        return success_response(
            PartDetailSerializer(part).data,
            "Part retrieved successfully!",
        )

    @extend_schema(**update_part_document)
    def partial_update(self, request, pk=None):
        part = get_instance(Part, pk)
        serializer = UpdatePartSerializer(
            part,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            part = serializer.save()
            return success_response(PartSerializer(part).data, "Part updated successfully!")
        return global_response_errors(serializer.errors)


class SourceDocumentPartViewSet(viewsets.ViewSet):
    def list(self, request, source_id=None):
        source_document = get_instance(SourceDocument, source_id)
        queryset = PartFilter(
            request.query_params,
            queryset=source_document.parts.select_related("preview_file").order_by(
                "sequence"
            ),
        ).qs
        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request)
        serializer = PartSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
