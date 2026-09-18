from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PartWorkflowViewSet, RevisionViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"v1/parts", PartWorkflowViewSet, basename="part-workflow")
router.register(r"v1/revisions", RevisionViewSet, basename="revision")

urlpatterns = [
    path("", include(router.urls)),
]
