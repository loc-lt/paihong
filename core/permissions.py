from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from core.constant import STAFF_ROLES, UserStatusEnum


def is_staff(user) -> bool:
    return getattr(user, "role", None) in STAFF_ROLES


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_staff(request.user)


class IsDesignRole(BasePermission):
    def has_permission(self, request, view):
        return is_staff(request.user)


class IsActiveUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.status != UserStatusEnum.ACTIVE.value:
            raise PermissionDenied("Your account is not active!")
        return True


def require_admin(user):
    if not is_staff(user):
        raise PermissionDenied()


def require_design(user):
    if not is_staff(user):
        raise PermissionDenied()


def can_manage_users(user):
    return is_staff(user)


def can_edit_design(user):
    return is_staff(user)
