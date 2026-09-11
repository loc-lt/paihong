from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from core.models import WorkflowStepDefinition, WorkflowTemplate
from core.paginators import CustomPaginator
from core.permissions import require_admin
from core.responses import success_response
from core.serializers.workflow_serializers import (
    CreateWorkflowTemplateSerializer,
    UpdateWorkflowTemplateSerializer,
    WorkflowStepDefinitionSerializer,
    WorkflowStepDefinitionWriteSerializer,
    WorkflowTemplateSerializer,
)
from core.services.part_workflow import sync_work_item_parts
from core.utils import get_instance, global_response_errors

from ..documents.workflow_documents import (
    create_workflow_step_document,
    create_workflow_template_document,
    get_workflow_step_document,
    get_workflow_steps_document,
    get_workflow_template_document,
    get_workflow_templates_document,
    sync_workflow_template_document,
    update_workflow_step_document,
    update_workflow_template_document,
)


class WorkflowTemplateViewSet(viewsets.ViewSet):
    @extend_schema(**get_workflow_templates_document)
    def list(self, request):
        require_admin(request.user)
        queryset = WorkflowTemplate.objects.prefetch_related(
            "template_steps__step"
        ).order_by("code")
        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request)
        serializer = WorkflowTemplateSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(**create_workflow_template_document)
    def create(self, request):
        require_admin(request.user)
        serializer = CreateWorkflowTemplateSerializer(data=request.data)
        if serializer.is_valid():
            template = serializer.save()
            return success_response(
                WorkflowTemplateSerializer(template).data,
                "Workflow template created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**get_workflow_template_document)
    def retrieve(self, request, pk=None):
        require_admin(request.user)
        template = get_instance(WorkflowTemplate, pk)
        template = WorkflowTemplate.objects.prefetch_related(
            "template_steps__step",
        ).get(pk=template.pk)
        return success_response(
            WorkflowTemplateSerializer(template).data,
            "Workflow template retrieved successfully!",
        )

    @extend_schema(**update_workflow_template_document)
    def partial_update(self, request, pk=None):
        require_admin(request.user)
        template = get_instance(WorkflowTemplate, pk)
        serializer = UpdateWorkflowTemplateSerializer(
            template,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            template = serializer.save()
            return success_response(
                WorkflowTemplateSerializer(template).data,
                "Workflow template updated successfully!",
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**sync_workflow_template_document)
    @action(detail=True, methods=["post"], url_path="sync-parts")
    def sync_parts(self, request, pk=None):
        require_admin(request.user)
        template = get_instance(WorkflowTemplate, pk)
        synced = 0
        for work_item in template.work_items.prefetch_related(
            "source_documents__parts"
        ):
            synced += sync_work_item_parts(work_item, user=request.user)
        return success_response(
            {"synced_parts": synced},
            "Workflow template synced to parts successfully!",
        )


class WorkflowStepDefinitionViewSet(viewsets.ViewSet):
    @extend_schema(**get_workflow_steps_document)
    def list(self, request):
        queryset = WorkflowStepDefinition.objects.order_by("sequence")
        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request)
        serializer = WorkflowStepDefinitionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(**create_workflow_step_document)
    def create(self, request):
        require_admin(request.user)
        serializer = WorkflowStepDefinitionWriteSerializer(data=request.data)
        if serializer.is_valid():
            step = serializer.save()
            return success_response(
                WorkflowStepDefinitionSerializer(step).data,
                "Workflow step created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**get_workflow_step_document)
    def retrieve(self, request, pk=None):
        step = get_instance(WorkflowStepDefinition, pk)
        return success_response(
            WorkflowStepDefinitionSerializer(step).data,
            "Workflow step retrieved successfully!",
        )

    @extend_schema(**update_workflow_step_document)
    def partial_update(self, request, pk=None):
        require_admin(request.user)
        step = get_instance(WorkflowStepDefinition, pk)
        serializer = WorkflowStepDefinitionWriteSerializer(
            step,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            step = serializer.save()
            return success_response(
                WorkflowStepDefinitionSerializer(step).data,
                "Workflow step updated successfully!",
            )
        return global_response_errors(serializer.errors)
