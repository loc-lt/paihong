from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser

from core.permissions import require_design
from core.serializers.ai_design_serializers import (
    CreateFilePRequestSerializer,
    CreateFilesCRequestSerializer,
    MergeImagesRequestSerializer,
    SmartSRequestSerializer,
)
from core.services.ai_design import (
    recall_create_file_p,
    recall_create_files_c,
    recall_merge_images,
    recall_smart_s,
)
from core.utils import global_response_errors

from ..documents.ai_design_documents import (
    create_file_p_document,
    create_files_c_document,
    merge_images_document,
    smart_s_document,
)


class AiDesignViewSet(viewsets.ViewSet):
    parser_classes = [JSONParser]

    def _recall(self, request, serializer_class, recall):
        require_design(request.user)
        serializer = serializer_class(data=request.data)
        if not serializer.is_valid():
            return global_response_errors(serializer.errors)
        try:
            return recall(serializer.validated_data)
        except ValidationError as exc:
            return global_response_errors(exc.detail)

    @extend_schema(**smart_s_document)
    @action(detail=False, methods=["post"], url_path="smart_s")
    def smart_s(self, request):
        return self._recall(request, SmartSRequestSerializer, recall_smart_s)

    @extend_schema(**merge_images_document)
    @action(detail=False, methods=["post"], url_path="merge_images")
    def merge_images(self, request):
        return self._recall(request, MergeImagesRequestSerializer, recall_merge_images)

    @extend_schema(**create_files_c_document)
    @action(detail=False, methods=["post"], url_path="create_files_c")
    def create_files_c(self, request):
        return self._recall(request, CreateFilesCRequestSerializer, recall_create_files_c)

    @extend_schema(**create_file_p_document)
    @action(detail=False, methods=["post"], url_path="create_file_p")
    def create_file_p(self, request):
        return self._recall(request, CreateFilePRequestSerializer, recall_create_file_p)
