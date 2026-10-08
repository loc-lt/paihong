import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from core.permissions import require_design
from core.serializers.ai_design_serializers import (
    AiFilePathProductCodeSerializer,
    CreateFileFcRequestSerializer,
    CreateFilePRequestSerializer,
    CreateFilesCRequestSerializer,
    CreateTrainDbAnchorRequestSerializer,
    CreateTrainDbRequestSerializer,
    MergeImagesRequestSerializer,
    SmartSRequestSerializer,
)
from core.services.ai_design import (
    recall_color_paths,
    recall_create_file_fc,
    recall_create_file_p,
    recall_create_files_c,
    recall_create_train_db,
    recall_create_train_db_anchor,
    recall_delete_anchors,
    recall_delete_paths,
    recall_merge_images,
    recall_rotate_svg,
    recall_smart_s,
    recall_split_regions,
)
from core.utils import global_response_errors

from ..documents.ai_design_documents import (
    color_paths_document,
    create_file_fc_document,
    create_file_p_document,
    create_files_c_document,
    create_train_db_anchor_document,
    create_train_db_document,
    delete_anchors_document,
    delete_paths_document,
    merge_images_document,
    rotate_svg_document,
    smart_s_document,
    split_regions_document,
)

logger = logging.getLogger(__name__)


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
        except Exception as exc:
            logger.exception("Unexpected AI recall failure in %s", recall.__name__)
            return Response(
                {
                    "status": False,
                    "message": (
                        f"[backend] Unexpected error in {recall.__name__}: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    "data": {
                        "stage": "backend",
                        "handler": recall.__name__,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    @extend_schema(**split_regions_document)
    @action(detail=False, methods=["post"], url_path="split_regions")
    def split_regions(self, request):
        return self._recall(request, AiFilePathProductCodeSerializer, recall_split_regions)

    @extend_schema(**rotate_svg_document)
    @action(detail=False, methods=["post"], url_path="rotate_svg")
    def rotate_svg(self, request):
        return self._recall(request, AiFilePathProductCodeSerializer, recall_rotate_svg)

    @extend_schema(**delete_paths_document)
    @action(detail=False, methods=["post"], url_path="delete_paths")
    def delete_paths(self, request):
        return self._recall(request, AiFilePathProductCodeSerializer, recall_delete_paths)

    @extend_schema(**delete_anchors_document)
    @action(detail=False, methods=["post"], url_path="delete_anchors")
    def delete_anchors(self, request):
        return self._recall(request, AiFilePathProductCodeSerializer, recall_delete_anchors)

    @extend_schema(**color_paths_document)
    @action(detail=False, methods=["post"], url_path="color_paths")
    def color_paths(self, request):
        return self._recall(request, AiFilePathProductCodeSerializer, recall_color_paths)

    @extend_schema(**create_train_db_document)
    @action(detail=False, methods=["post"], url_path="create_train_db")
    def create_train_db(self, request):
        return self._recall(request, CreateTrainDbRequestSerializer, recall_create_train_db)

    @extend_schema(**create_train_db_anchor_document)
    @action(detail=False, methods=["post"], url_path="create_train_db_anchor")
    def create_train_db_anchor(self, request):
        return self._recall(
            request,
            CreateTrainDbAnchorRequestSerializer,
            recall_create_train_db_anchor,
        )

    @extend_schema(**create_file_fc_document)
    @action(detail=False, methods=["post"], url_path="create_file_fc")
    def create_file_fc(self, request):
        return self._recall(request, CreateFileFcRequestSerializer, recall_create_file_fc)
