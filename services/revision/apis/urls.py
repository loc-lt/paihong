from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DesignFileRevisionViewSet,
    DesignWorkspaceViewSet,
    PartWorkflowViewSet,
    RevisionViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register(r"v1/parts", PartWorkflowViewSet, basename="part-workflow")
router.register(r"v1/parts", DesignWorkspaceViewSet, basename="design-workspace")
router.register(r"v1/revisions", RevisionViewSet, basename="revision")
router.register(
    r"v1/design_file_revisions",
    DesignFileRevisionViewSet,
    basename="design-file-revision",
)

urlpatterns = [
    path("", include(router.urls)),
]
