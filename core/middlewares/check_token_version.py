from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from core.constant import EXCLUDE_AUTH_PATH
from core.utils import get_access_token_from_request, request_path_is_excluded


class TokenVersionMiddleware(BasePermission):
    def has_permission(self, request: Request, view):
        if request_path_is_excluded(request, EXCLUDE_AUTH_PATH):
            return True
        raw_token = get_access_token_from_request(request)
        if not raw_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")
        try:
            access_token = AccessToken(raw_token)
        except TokenError:
            raise AuthenticationFailed("Token is invalid!")
        token = access_token.payload.get("token_version", None)
        if request.user and request.user.is_token_version_valid(token):
            return True
        raise AuthenticationFailed("Token is invalid due to version mismatch!")
