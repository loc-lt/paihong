from drf_spectacular.utils import OpenApiResponse

from core.serializers.workflow_serializers import (
    CreateWorkflowTemplateSerializer,
    UpdateWorkflowTemplateSerializer,
    WorkflowStepDefinitionSerializer,
    WorkflowStepDefinitionWriteSerializer,
    WorkflowTemplateSerializer,
)

get_workflow_templates_document = {
    "summary": "List workflow templates.",
    "responses": {200: WorkflowTemplateSerializer(many=True)},
}

create_workflow_template_document = {
    "summary": "Create workflow template.",
    "request": CreateWorkflowTemplateSerializer,
    "responses": {201: WorkflowTemplateSerializer},
}

get_workflow_template_document = {
    "summary": "Get workflow template detail.",
    "responses": {200: WorkflowTemplateSerializer},
}

update_workflow_template_document = {
    "summary": "Update workflow template.",
    "request": UpdateWorkflowTemplateSerializer,
    "responses": {200: WorkflowTemplateSerializer},
}

sync_workflow_template_document = {
    "summary": "Sync template steps to all related parts.",
    "responses": {200: OpenApiResponse(description="Synced")},
}

get_workflow_steps_document = {
    "summary": "List workflow step definitions.",
    "responses": {200: WorkflowStepDefinitionSerializer(many=True)},
}

create_workflow_step_document = {
    "summary": "Create workflow step definition.",
    "request": WorkflowStepDefinitionWriteSerializer,
    "responses": {201: WorkflowStepDefinitionSerializer},
}

get_workflow_step_document = {
    "summary": "Get workflow step definition.",
    "responses": {200: WorkflowStepDefinitionSerializer},
}

update_workflow_step_document = {
    "summary": "Update workflow step definition.",
    "request": WorkflowStepDefinitionWriteSerializer,
    "responses": {200: WorkflowStepDefinitionSerializer},
}
