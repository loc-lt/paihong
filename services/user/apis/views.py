from drf_spectacular.utils import extend_schema
from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenRefreshView

from core.jwt import MyTokenObtainPairSerializer
from core.paginators import CustomPaginator
from core.permissions import can_manage_users
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
from core.models import User
from core.utils import get_deleted_instance, get_instance, global_response_errors

from .documents import (
    create_user_document,
    delete_user_document,
    get_user_document,
    get_users_document,
    login_user_document,
    logout_user_document,
    refresh_token_document,
    register_user_document,
    restore_user_document,
    update_user_document,
)


class AuthenViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(**register_user_document)
    @action(detail=False, methods=["post"], url_path="register")
    def create_user(self, request):
        serializer = RegisterUserSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": True, "message": "User created successfully!"},
                status=status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**login_user_document)
    @action(methods=["post"], detail=False, url_path="login")
    def login_user(self, request):
        serializer = UserLoginSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user = authenticate(
                request,
                username=serializer.validated_data["username"].strip(),
                password=serializer.validated_data["password"],
            )
            if user and user.is_active:
                refresh = MyTokenObtainPairSerializer.get_token(user)
                return Response(
                    {
                        "status": True,
                        "data": UserSerializerWithToken(
                            user,
                            context={
                                "access_token": str(refresh.access_token),
                                "refresh_token": str(refresh),
                            },
                        ).data,
                        "message": "Login successfully!",
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"status": False, "message": "Username or password is incorrect!"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**logout_user_document)
    @action(methods=["post"], detail=False, url_path="logout")
    def logout_user(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return global_response_errors(serializer.errors)

        user = serializer.validated_data.get("user")
        refresh_token = serializer.validated_data.get("token")
        if user:
            user.set_new_token_version()
        if refresh_token:
            try:
                refresh_token.blacklist()
            except TokenError:
                pass
        return Response(
            {"status": True, "message": "Logout successfully!"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], detail=False, url_path="me")
    def me(self, request):
        return Response(
            {
                "status": True,
                "data": UserSerializer(request.user).data,
                "message": "Current user retrieved successfully!",
            },
            status=status.HTTP_200_OK,
        )


class CustomTokenRefreshView(TokenRefreshView):
    @extend_schema(**refresh_token_document)
    def post(self, request, *args, **kwargs):
        serializer = RefreshTokenSerializer(data=request.data)
        if serializer.is_valid():
            access_token = serializer.validated_data["access_token"]
            refresh_token = serializer.validated_data.get("refresh_token")
            user = serializer.validated_data.get("user")
            return Response(
                {
                    "status": True,
                    "data": UserSerializerWithToken(
                        user,
                        context={
                            "access_token": str(access_token),
                            "refresh_token": str(refresh_token),
                        },
                    ).data,
                    "message": "Refresh token successfully!",
                },
                status=status.HTTP_200_OK,
            )
        return global_response_errors(serializer.errors)


class UserViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _require_admin(self, request):
        if not can_manage_users(request.user):
            raise PermissionDenied()

    @extend_schema(**get_users_document)
    def list(self, request):
        self._require_admin(request)
        queryset = User.objects.order_by("username")
        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(**create_user_document)
    def create(self, request):
        self._require_admin(request)
        serializer = CreateUserSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "status": True,
                    "data": UserSerializer(user).data,
                    "message": "User created successfully!",
                },
                status=status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**get_user_document)
    def retrieve(self, request, pk=None):
        self._require_admin(request)
        user = get_instance(User, pk)
        return Response(
            {
                "status": True,
                "data": UserSerializer(user).data,
                "message": "User retrieved successfully!",
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(**update_user_document)
    def partial_update(self, request, pk=None):
        self._require_admin(request)
        user = get_instance(User, pk)
        serializer = UpdateUserSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "status": True,
                    "data": UserSerializer(user).data,
                    "message": "User updated successfully!",
                },
                status=status.HTTP_200_OK,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**delete_user_document)
    def destroy(self, request, pk=None):
        self._require_admin(request)
        user = get_instance(User, pk)
        user.delete()
        return Response(
            {"status": True, "message": "User deleted successfully!"},
            status=status.HTTP_200_OK,
        )

    @extend_schema(**restore_user_document)
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        self._require_admin(request)
        user = get_deleted_instance(User, pk)
        user.restore(strict=False)
        user.refresh_from_db()
        return Response(
            {
                "status": True,
                "data": UserSerializer(user).data,
                "message": "User restored successfully!",
            },
            status=status.HTTP_200_OK,
        )
