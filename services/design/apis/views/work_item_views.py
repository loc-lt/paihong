from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from core.filters import PartFilter, SourceDocumentFilter, WorkItemFilter
from core.models import Part, SourceDocument, WorkItem

from core.paginators import CustomPaginator

from core.responses import success_response

from core.serializers.part_serializers import PartSerializer

from core.serializers.source_document_serializers import SourceDocumentSerializer

from core.serializers.work_item_process_serializers import (

    ProcessWorkItemResultSerializer,

    ProcessWorkItemSerializer,

)

from core.serializers.work_item_serializers import (
    UpdateWorkItemSerializer,
    WorkItemDetailSerializer,
    WorkItemSerializer,
)

from core.utils import get_instance, global_response_errors



from ..documents.work_item_documents import (

    create_work_item_document,

    delete_work_item_document,

    get_source_documents_document,

    get_work_item_document,

    get_work_item_parts_document,

    get_work_items_document,

    update_work_item_document,

)





def _annotate_parts_count(queryset):
    return queryset.annotate(
        parts_count=Count("source_documents__parts", distinct=True),
    )


def _work_item_detail_queryset():
    parts_qs = Part.objects.select_related(
        "preview_file",
        "source_document",
    ).order_by("source_document__sequence", "sequence")
    source_documents_qs = SourceDocument.objects.select_related("file").prefetch_related(
        Prefetch("parts", queryset=parts_qs),
    ).order_by("sequence")
    return _annotate_parts_count(
        WorkItem.objects.select_related(
            "created_by",
            "updated_by",
            "workflow_template",
        ).prefetch_related(
            Prefetch("source_documents", queryset=source_documents_qs),
        )
    )


class WorkItemViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]



    @extend_schema(**get_work_items_document)

    def list(self, request):

        queryset = WorkItemFilter(

            request.query_params,

            queryset=_annotate_parts_count(
                WorkItem.objects.select_related(
                    "created_by",
                    "updated_by",
                    "workflow_template",
                )
            ).order_by("-created"),

        ).qs

        paginator = CustomPaginator()

        page = paginator.paginate_queryset(queryset, request)

        serializer = WorkItemSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)



    @extend_schema(**create_work_item_document)

    def create(self, request):

        serializer = ProcessWorkItemSerializer(

            data=request.data,

            context={"request": request},

        )

        if serializer.is_valid():

            result = serializer.save()

            return success_response(

                ProcessWorkItemResultSerializer(result).data,

                "Work item processed successfully!",

                status.HTTP_201_CREATED,

            )

        return global_response_errors(serializer.errors)



    @extend_schema(**get_work_item_document)

    def retrieve(self, request, pk=None):
        work_item = get_instance(_work_item_detail_queryset(), pk)
        return success_response(
            WorkItemDetailSerializer(work_item).data,
            "Work item retrieved successfully!",
        )



    @extend_schema(**update_work_item_document)

    def partial_update(self, request, pk=None):

        work_item = get_instance(WorkItem, pk)

        serializer = UpdateWorkItemSerializer(

            work_item,

            data=request.data,

            partial=True,

            context={"request": request},

        )

        if serializer.is_valid():

            work_item = serializer.save()
            work_item = _annotate_parts_count(
                WorkItem.objects.select_related("workflow_template")
            ).get(pk=work_item.pk)

            return success_response(
                WorkItemSerializer(work_item).data,

                "Work item updated successfully!",

            )

        return global_response_errors(serializer.errors)



    @extend_schema(**delete_work_item_document)

    def destroy(self, request, pk=None):

        work_item = get_instance(WorkItem, pk)

        work_item.delete()

        return success_response(None, "Work item deleted successfully!")



    @extend_schema(**get_source_documents_document)

    @action(detail=True, methods=["get"], url_path="source_documents")

    def source_documents(self, request, pk=None):

        work_item = get_instance(WorkItem, pk)

        queryset = SourceDocumentFilter(

            request.query_params,

            queryset=work_item.source_documents.select_related("file").order_by(

                "sequence"

            ),

        ).qs

        paginator = CustomPaginator()

        page = paginator.paginate_queryset(queryset, request)

        serializer = SourceDocumentSerializer(page, many=True)

        return paginator.get_paginated_response(serializer.data)



    @extend_schema(**get_work_item_parts_document)

    @action(detail=True, methods=["get"], url_path="parts")

    def parts(self, request, pk=None):

        work_item = get_instance(WorkItem, pk)

        queryset = PartFilter(

            request.query_params,

            queryset=Part.objects.filter(source_document__work_item=work_item)

            .select_related("preview_file", "source_document")

            .order_by("source_document__sequence", "sequence"),

        ).qs

        serializer = PartSerializer(queryset, many=True)
        return success_response(
            serializer.data,
            "Work item parts retrieved successfully!",
        )

