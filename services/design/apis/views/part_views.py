from drf_spectacular.openapi import AutoSchema
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from core.filters import PartFilter
from core.models import Part, SourceDocument
from core.paginators import CustomPaginator
from core.permissions import require_design
from core.responses import success_response
from core.serializers.part_serializers import (
    BulkCreatePartSerializer,
    BulkDeletePartSerializer,
    PartDetailSerializer,
    PartSerializer,
    UpdatePartSerializer,
)
from core.services.part_manage import delete_parts
from core.utils import get_instance, global_response_errors

from ..documents.part_documents import (
    create_part_document,
    delete_part_document,
    get_part_document,
    list_source_document_parts_document,
    update_part_document,
)


class PartSchema(AutoSchema):
    """Spectacular drops request bodies on DELETE. Bulk delete needs one."""

    def _get_request_body(self, direction="request"):
        if self.method != "DELETE":
            return super()._get_request_body(direction)
        saved_method = self.method
        self.method = "POST"
        try:
            return super()._get_request_body(direction)
        finally:
            self.method = saved_method


def _load_part_details(parts):
    ids = [part.pk for part in parts]
    rows = Part.objects.select_related(
        "preview_file",
        "source_document__file",
        "source_document__svg_file",
    ).filter(pk__in=ids)
    by_id = {row.pk: row for row in rows}
    return [by_id[part_id] for part_id in ids]


def _part_detail_response(part, message, status_code=status.HTTP_200_OK):
    return success_response(
        PartDetailSerializer(_load_part_details([part])[0]).data,
        message,
        status_code,
    )


class PartViewSet(viewsets.ViewSet):
    schema = PartSchema()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(**create_part_document)
    def create(self, request):
        require_design(request.user)
        serializer = BulkCreatePartSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            parts = serializer.save()
            return success_response(
                PartDetailSerializer(_load_part_details(parts), many=True).data,
                "Parts created successfully!",
                status.HTTP_201_CREATED,
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
    def bulk_destroy(self, request):
        require_design(request.user)
        serializer = BulkDeletePartSerializer(data=request.data)
        if not serializer.is_valid():
            return global_response_errors(serializer.errors)
        parts = list(Part.objects.filter(pk__in=serializer.validated_data["ids"]))
        delete_parts(parts, user=request.user)
        return success_response(
            {"deleted_count": len(parts)},
            "Parts deleted successfully!",
        )


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
