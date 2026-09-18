from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from core.constant import (
    ALLOWED_AVATAR_EXTENSIONS,
    AVATAR_MAX_SIZE,
    UserRoleEnum,
    UserStatusEnum,
)
from core.models import User
from core.serializers.fields import coerce_optional_string
from core.serializers.file_serializers import FileObjectSerializer
from core.services.user import assign_user_avatar


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar = FileObjectSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "status",
            "avatar",
            "full_name",
            "created",
            "modified",
        ]
        read_only_fields = fields


class UserSerializerWithToken(UserSerializer):
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["access_token", "refresh_token"]
        read_only_fields = fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["access_token"] = self.context.get("access_token")
        representation["refresh_token"] = self.context.get("refresh_token")
        return representation


class CreateUserSerializer(serializers.ModelSerializer):
    avatar = serializers.FileField(
        required=False,
        error_messages={
            "required": "Avatar must be a valid upload!",
            "invalid": "Avatar must be a valid upload!",
            "null": "Avatar must be a valid upload!",
            "empty": "Avatar cannot be empty!",
            "no_name": "Avatar must be a valid upload!",
        },
    )
    username = serializers.CharField(
        max_length=150,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Username is required!",
            "blank": "Username cannot be empty!",
            "null": "Username is required!",
            "invalid": "Username must be a string!",
            "max_length": "Username cannot exceed 150 characters!",
        },
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        allow_blank=False,
        error_messages={
            "required": "Password is required!",
            "blank": "Password cannot be empty!",
            "null": "Password is required!",
            "invalid": "Password must be a string!",
        },
    )
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "invalid": "First name must be a string!",
            "max_length": "First name cannot exceed 150 characters!",
        },
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "invalid": "Last name must be a string!",
            "max_length": "Last name cannot exceed 150 characters!",
        },
    )
    role = serializers.ChoiceField(
        choices=UserRoleEnum.choices,
        required=False,
        default=UserRoleEnum.CUSTOMER.value,
        error_messages={
            "invalid_choice": "Invalid user role!",
            "null": "Invalid user role!",
        },
    )
    status = serializers.ChoiceField(
        choices=UserStatusEnum.choices,
        required=False,
        default=UserStatusEnum.ACTIVE.value,
        error_messages={
            "invalid_choice": "Invalid user status!",
            "null": "Invalid user status!",
        },
    )

    class Meta:
        model = User
        fields = [
            "username",
            "password",
            "first_name",
            "last_name",
            "role",
            "status",
            "avatar",
        ]

    def validate_username(self, value):
        username = value.strip()
        if User.global_objects.filter(username=username).exists():
            raise serializers.ValidationError("Username already exists!")
        return username

    def validate_first_name(self, value):
        return coerce_optional_string(value)

    def validate_last_name(self, value):
        return coerce_optional_string(value)

    def validate_avatar(self, value):
        if value.size > AVATAR_MAX_SIZE:
            raise serializers.ValidationError("Avatar must be smaller than 3 MB!")
        filename = value.name or ""
        if "." not in filename:
            raise serializers.ValidationError("Avatar must have a valid extension!")
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_AVATAR_EXTENSIONS:
            allowed = ", ".join(ext.upper() for ext in ALLOWED_AVATAR_EXTENSIONS)
            raise serializers.ValidationError(f"Avatar must be one of: {allowed}!")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        return value

    def create(self, validated_data):
        avatar_file = validated_data.pop("avatar", None)
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        request = self.context.get("request")
        created_by = getattr(request, "user", None) if request else None
        return assign_user_avatar(user, avatar_file, created_by=created_by)


class UpdateUserSerializer(serializers.ModelSerializer):
    avatar = serializers.FileField(
        required=False,
        error_messages={
            "required": "Avatar must be a valid upload!",
            "invalid": "Avatar must be a valid upload!",
            "null": "Avatar must be a valid upload!",
            "empty": "Avatar cannot be empty!",
            "no_name": "Avatar must be a valid upload!",
        },
    )
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "invalid": "First name must be a string!",
            "max_length": "First name cannot exceed 150 characters!",
        },
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "invalid": "Last name must be a string!",
            "max_length": "Last name cannot exceed 150 characters!",
        },
    )
    role = serializers.ChoiceField(
        choices=UserRoleEnum.choices,
        required=False,
        error_messages={
            "invalid_choice": "Invalid user role!",
            "null": "Invalid user role!",
        },
    )
    status = serializers.ChoiceField(
        choices=UserStatusEnum.choices,
        required=False,
        error_messages={
            "invalid_choice": "Invalid user status!",
            "null": "Invalid user status!",
        },
    )
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        allow_null=True,
        error_messages={
            "blank": "Password cannot be empty!",
            "invalid": "Password must be a string!",
        },
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "role",
            "status",
            "password",
            "avatar",
        ]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_first_name(self, value):
        return coerce_optional_string(value)

    def validate_last_name(self, value):
        return coerce_optional_string(value)

    def validate_avatar(self, value):
        if value.size > AVATAR_MAX_SIZE:
            raise serializers.ValidationError("Avatar must be smaller than 3 MB!")
        filename = value.name or ""
        if "." not in filename:
            raise serializers.ValidationError("Avatar must have a valid extension!")
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_AVATAR_EXTENSIONS:
            allowed = ", ".join(ext.upper() for ext in ALLOWED_AVATAR_EXTENSIONS)
            raise serializers.ValidationError(f"Avatar must be one of: {allowed}!")
        return value

    def validate_password(self, value):
        if not value:
            return value
        try:
            validate_password(value)
        except ValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        return value

    def update(self, instance, validated_data):
        avatar_file = validated_data.pop("avatar", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        request = self.context.get("request")
        created_by = getattr(request, "user", None) if request else None
        return assign_user_avatar(instance, avatar_file, created_by=created_by)


class RegisterUserSerializer(CreateUserSerializer):
    class Meta(CreateUserSerializer.Meta):
        fields = [
            "username",
            "password",
            "first_name",
            "last_name",
            "avatar",
        ]


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=150,
        trim_whitespace=True,
        error_messages={
            "required": "Please enter your username!",
            "blank": "Username cannot be empty!",
            "null": "Please enter your username!",
            "invalid": "Username must be a string!",
            "max_length": "Username cannot exceed 150 characters!",
        },
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
        error_messages={
            "required": "Please enter your password!",
            "blank": "Password cannot be empty!",
            "null": "Please enter your password!",
            "invalid": "Password must be a string!",
        },
    )


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Refresh token is required!",
            "blank": "Refresh token cannot be empty!",
            "null": "Refresh token is required!",
            "invalid": "Refresh token must be a string!",
        },
    )

    def validate_refresh_token(self, value):
        try:
            token = RefreshToken(value)
        except (TokenError, InvalidToken) as exc:
            if "blacklisted" in str(exc).lower():
                return None
            raise serializers.ValidationError("Refresh token is invalid!")
        return token

    def validate(self, attrs):
        token = attrs.get("refresh_token")
        if token is None:
            attrs["token"] = None
            attrs["user"] = None
            return attrs
        user_id = token.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(
            **{api_settings.USER_ID_FIELD: user_id}
        ).first()
        attrs["token"] = token
        attrs["user"] = user
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Refresh token is required!",
            "blank": "Refresh token cannot be empty!",
            "null": "Refresh token is required!",
            "invalid": "Refresh token must be a string!",
        },
    )

    def validate(self, attrs):
        raw_token = attrs.get("refresh")
        try:
            refresh = RefreshToken(raw_token)
            user_id = refresh[api_settings.USER_ID_CLAIM]
            user = User.objects.get(**{api_settings.USER_ID_FIELD: user_id})
            if not user.is_active:
                raise AuthenticationFailed("User account is inactive!")
            attrs["access_token"] = refresh.access_token
            attrs["refresh_token"] = refresh
            attrs["user"] = user
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found!")
        except TokenError as exc:
            raise AuthenticationFailed(f"{str(exc)}!")
        except InvalidToken as exc:
            raise AuthenticationFailed(f"{str(exc)}!")
        return attrs
