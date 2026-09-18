from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from core.constant import EXCLUDE_AUTH_PATH
from core.utils import request_path_is_excluded


class AuthenticateMiddleware(IsAuthenticated):
    def has_permission(self, request: Request, view):
        if request_path_is_excluded(request, EXCLUDE_AUTH_PATH):
            return True
        return super().has_permission(request, view)
