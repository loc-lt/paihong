from drf_spectacular.utils import OpenApiResponse

from core.serializers.user_serializers import (
    CreateUserSerializer,
    LogoutSerializer,
    RefreshTokenSerializer,
    RegisterUserSerializer,
    UpdateUserSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserSerializerWithToken,
)

register_user_document = {
    "summary": "Create new user.",
    "description": (
        "Register a new account. Use multipart/form-data when uploading an avatar "
        "(PNG, JPG, JPEG, WEBP; max 3 MB)."
    ),
    "request": RegisterUserSerializer,
    "responses": {201: OpenApiResponse(description="Created")},
}

login_user_document = {
    "summary": "Login to the system.",
    "request": UserLoginSerializer,
    "responses": {200: UserSerializerWithToken},
}

logout_user_document = {
    "summary": "Logout of the system.",
    "description": (
        "Public endpoint. Send `refresh_token` from login to invalidate it "
        "and revoke existing access tokens."
    ),
    "request": LogoutSerializer,
    "responses": {200: OpenApiResponse(description="Logged out")},
}

refresh_token_document = {
    "summary": "Refresh token.",
    "request": RefreshTokenSerializer,
    "responses": {200: UserSerializerWithToken},
}

get_users_document = {
    "summary": "List users.",
    "responses": {200: UserSerializer(many=True)},
}

create_user_document = {
    "summary": "Create user.",
    "description": (
        "Admin creates a user. Use multipart/form-data when uploading an avatar "
        "(PNG, JPG, JPEG, WEBP; max 3 MB)."
    ),
    "request": CreateUserSerializer,
    "responses": {201: UserSerializer},
}

get_user_document = {
    "summary": "Get user detail.",
    "responses": {200: UserSerializer},
}

update_user_document = {
    "summary": "Update user.",
    "description": (
        "Admin updates a user. Use multipart/form-data when uploading an avatar "
        "(PNG, JPG, JPEG, WEBP; max 3 MB)."
    ),
    "request": UpdateUserSerializer,
    "responses": {200: UserSerializer},
}

delete_user_document = {
    "summary": "Soft delete user.",
    "responses": {200: OpenApiResponse(description="Deleted")},
}

restore_user_document = {
    "summary": "Restore soft-deleted user.",
    "responses": {200: UserSerializer},
}
