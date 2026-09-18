from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PartViewSet,
    SourceDocumentPartViewSet,
    SourceDocumentViewSet,
    WorkItemViewSet,
    WorkflowStepDefinitionViewSet,
    WorkflowTemplateViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"v1/work_items", WorkItemViewSet, basename="work-item")
router.register(r"v1/source_documents", SourceDocumentViewSet, basename="source-document")
router.register(r"v1/parts", PartViewSet, basename="part")
router.register(r"v1/workflow_templates", WorkflowTemplateViewSet, basename="workflow-template")
router.register(r"v1/workflow_steps", WorkflowStepDefinitionViewSet, basename="workflow-step")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "v1/source_documents/<uuid:source_id>/parts/",
        SourceDocumentPartViewSet.as_view({"get": "list"}),
        name="source-document-parts",
    ),
]
