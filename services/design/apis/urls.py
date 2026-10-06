from django.urls import include, path
from rest_framework.routers import DefaultRouter, Route

from .views import (
    ColorViewSet,
    PartViewSet,
    SourceDocumentPartViewSet,
    SourceDocumentViewSet,
    SystemColorViewSet,
    WeavingMachineBarViewSet,
    WeavingMachineSpecViewSet,
    WeavingMachineViewSet,
    WorkItemViewSet,
    WorkflowStepDefinitionViewSet,
    WorkflowTemplateViewSet,
)

class PartRouter(DefaultRouter):
    """List route also accepts DELETE, mapped to PartViewSet.bulk_destroy."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.routes = [
            Route(
                url=route.url,
                mapping=(
                    {**route.mapping, "delete": "bulk_destroy"}
                    if isinstance(route, Route) and route.mapping.get("post") == "create"
                    else route.mapping
                ),
                name=route.name,
                detail=route.detail,
                initkwargs=route.initkwargs,
            )
            if isinstance(route, Route)
            else route
            for route in self.routes
        ]


router = DefaultRouter(trailing_slash=False)
part_router = PartRouter(trailing_slash=False)
router.register(r"v1/work_items", WorkItemViewSet, basename="work-item")
router.register(r"v1/source_documents", SourceDocumentViewSet, basename="source-document")
part_router.register(r"v1/parts", PartViewSet, basename="part")
router.register(r"v1/workflow_templates", WorkflowTemplateViewSet, basename="workflow-template")
router.register(r"v1/workflow_steps", WorkflowStepDefinitionViewSet, basename="workflow-step")
router.register(r"v1/colors", ColorViewSet, basename="color")
router.register(r"v1/system_colors", SystemColorViewSet, basename="system-color")
router.register(r"v1/weaving_machines", WeavingMachineViewSet, basename="weaving-machine")
router.register(
    r"v1/weaving_machine_specs",
    WeavingMachineSpecViewSet,
    basename="weaving-machine-spec",
)
router.register(r"v1/weaving_machine_bars", WeavingMachineBarViewSet, basename="weaving-machine-bar")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(part_router.urls)),
    path(
        "v1/source_documents/<uuid:source_id>/parts/",
        SourceDocumentPartViewSet.as_view({"get": "list"}),
        name="source-document-parts",
    ),
]
