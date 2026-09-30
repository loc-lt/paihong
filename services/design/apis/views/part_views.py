from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from core.filters import PartFilter
from core.models import Part, SourceDocument
from core.paginators import CustomPaginator
from core.permissions import require_design
from core.responses import success_response
from core.serializers.part_serializers import (
    CreatePartSerializer,
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)
from core.services.part_manage import delete_part
from core.utils import get_instance, global_response_errors

from ..documents.part_documents import (
    create_part_document,
    delete_part_document,
    get_part_document,
    list_source_document_parts_document,
    update_part_document,
)


def _part_detail_response(part, message, status_code=status.HTTP_200_OK):
    part = Part.objects.select_related(
        "preview_file",
        "source_document__file",
        "source_document__svg_file",
    ).get(pk=part.pk)
    return success_response(PartDetailSerializer(part).data, message, status_code)


class PartViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(**create_part_document)
    def create(self, request):
        require_design(request.user)
        serializer = CreatePartSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            part = serializer.save()
            return _part_detail_response(
                part, "Part created successfully!", status.HTTP_201_CREATED
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**get_part_document)
    def retrieve(self, request, pk=None):
        part = get_instance(Part, pk)
        return _part_detail_response(part, "Part retrieved successfully!")

    @extend_schema(**update_part_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
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

    @extend_schema(**delete_part_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        part = get_instance(Part, pk)
        delete_part(part, user=request.user)
        return success_response(None, "Part deleted successfully!")


class SourceDocumentPartViewSet(viewsets.ViewSet):
    @extend_schema(**list_source_document_parts_document)
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
