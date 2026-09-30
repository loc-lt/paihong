from rest_framework import serializers

from core.constant import POSITIVE_SMALL_INTEGER_MAX_VALUE
from core.models import ColorDefinition, UserColorPreference
from core.services.color_palette import (
    custom_code_exists,
    custom_hex_exists,
    system_code_exists,
    system_hex_exists,
)
from core.services.design_grid.color_code import normalize_color_code


class ColorDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorDefinition
        fields = [
            "id",
            "code",
            "hex_value",
            "name",
            "display_order",
            "is_system",
        ]
        read_only_fields = fields


class UserColorPreferenceSerializer(serializers.ModelSerializer):
    hex_value = serializers.CharField(source="custom_hex", read_only=True)
    name = serializers.CharField(source="custom_name", read_only=True)

    class Meta:
        model = UserColorPreference
        fields = [
            "id",
            "code",
            "hex_value",
            "name",
            "display_order",
            "created",
            "modified",
        ]
        read_only_fields = fields


class MergedColorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.IntegerField()
    hex_value = serializers.CharField()
    name = serializers.CharField()
    display_order = serializers.IntegerField(
        help_text="Sort order within its block (system colors, then custom colors)."
    )
    is_system = serializers.BooleanField()
    is_custom = serializers.BooleanField()


def _validate_hex(value: str) -> str:
    try:
        return normalize_color_code(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc)) from exc


COLOR_CODE_ERROR_MESSAGES = {
    "required": "Color code is required!",
    "null": "Color code is required!",
    "invalid": "Color code must be an integer!",
    "min_value": "Color code must be at least 1!",
    "max_value": "Color code is too large!",
}
HEX_VALUE_ERROR_MESSAGES = {
    "required": "Hex value is required!",
    "blank": "Hex value cannot be empty!",
    "null": "Hex value is required!",
}


class SystemColorWriteSerializer(serializers.Serializer):
    code = serializers.IntegerField(
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        error_messages=COLOR_CODE_ERROR_MESSAGES,
    )
    hex_value = serializers.CharField(error_messages=HEX_VALUE_ERROR_MESSAGES)
    name = serializers.CharField(
        max_length=100,
        error_messages={
            "required": "Color name is required!",
            "blank": "Color name cannot be empty!",
            "null": "Color name is required!",
            "max_length": "Color name cannot exceed 100 characters!",
        },
    )
    display_order = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        default=0,
    )

    def validate_hex_value(self, value):
        return _validate_hex(value)

    def validate(self, attrs):
        if self.partial and not attrs:
            raise serializers.ValidationError("At least one field is required!")
        exclude_pk = self.instance.pk if self.instance else None
        if "code" in attrs and system_code_exists(code=attrs["code"], exclude_pk=exclude_pk):
            raise serializers.ValidationError(
                {"code": "Color code already exists in system colors!"}
            )
        if "hex_value" in attrs and system_hex_exists(
            hex_value=attrs["hex_value"], exclude_pk=exclude_pk
        ):
            raise serializers.ValidationError(
                {"hex_value": "Hex value already exists in system colors!"}
            )
        return attrs

    def create(self, validated_data):
        return ColorDefinition.objects.create(is_system=True, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserColorPreferenceCreateSerializer(serializers.Serializer):
    code = serializers.IntegerField(
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        error_messages={
            "required": "Color code is required!",
            "null": "Color code is required!",
            "invalid": "Color code must be an integer!",
            "min_value": "Color code must be at least 1!",
            "max_value": "Color code is too large!",
        },
    )
    hex_value = serializers.CharField(
        error_messages={
            "required": "Hex value is required!",
            "blank": "Hex value cannot be empty!",
            "null": "Hex value is required!",
        },
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=100,
    )
    display_order = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        default=0,
    )

    def validate_hex_value(self, value):
        return _validate_hex(value)

    def validate(self, attrs):
        user = self.context["request"].user
        code = attrs["code"]
        hex_value = attrs["hex_value"]
        if custom_code_exists(user=user, code=code):
            raise serializers.ValidationError(
                {"code": "Color code already exists in your custom colors!"}
            )
        if custom_hex_exists(user=user, hex_value=hex_value):
            raise serializers.ValidationError(
                {
                    "hex_value": (
                        "Hex value already exists in system colors "
                        "or your custom colors!"
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        return UserColorPreference.objects.create(
            user=self.context["request"].user,
            code=validated_data["code"],
            custom_hex=validated_data["hex_value"],
            custom_name=validated_data.get("name") or "",
            display_order=validated_data.get("display_order") or 0,
        )


class UserColorPreferenceUpdateSerializer(serializers.Serializer):
    code = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        error_messages={
            "invalid": "Color code must be an integer!",
            "min_value": "Color code must be at least 1!",
            "max_value": "Color code is too large!",
        },
    )
    hex_value = serializers.CharField(required=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    display_order = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
    )

    def validate_hex_value(self, value):
        return _validate_hex(value)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required!")
        user = self.context["request"].user
        instance = self.instance
        code = attrs.get("code", instance.code)
        hex_value = attrs.get("hex_value", instance.custom_hex)
        if custom_code_exists(user=user, code=code, exclude_pk=instance.pk):
            raise serializers.ValidationError(
                {"code": "Color code already exists in your custom colors!"}
            )
        if custom_hex_exists(user=user, hex_value=hex_value, exclude_pk=instance.pk):
            raise serializers.ValidationError(
                {
                    "hex_value": (
                        "Hex value already exists in system colors "
                        "or your custom colors!"
                    )
                }
            )
        return attrs

    def update(self, instance, validated_data):
        if "code" in validated_data:
            instance.code = validated_data["code"]
        if "hex_value" in validated_data:
            instance.custom_hex = validated_data["hex_value"]
        if "name" in validated_data:
            instance.custom_name = validated_data["name"] or ""
        if "display_order" in validated_data:
            instance.display_order = validated_data["display_order"]
        instance.save()
        return instance
