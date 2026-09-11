from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from core.constant import EXCLUDE_ACTIVE_PATH, UserStatusEnum
from core.utils import path_is_excluded


class ActiveAccountMiddleware(BasePermission):
    def has_permission(self, request: Request, view):
        current_route = request.resolver_match.route
        if path_is_excluded(current_route, EXCLUDE_ACTIVE_PATH):
            return True
        if request.user.status == UserStatusEnum.ACTIVE.value:
            return True
        raise PermissionDenied("Your account has not been activated!")
