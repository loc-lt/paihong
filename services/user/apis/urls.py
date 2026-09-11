from django.urls import include, path
from rest_framework import routers

from .views import AuthenViewSet, CustomTokenRefreshView, UserViewSet

router = routers.DefaultRouter()
router.register(r"v1/auth", AuthenViewSet, basename="auth")
router.register(r"v1/users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("v1/auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
]
