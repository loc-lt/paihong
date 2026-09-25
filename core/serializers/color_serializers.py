from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.models import ColorDefinition, UserColorPreference
from core.services.design_grid.color_code import normalize_color_code


class ColorDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorDefinition
        fields = [
            "id",
            "code",
            "hex_value",
            "name",
            "default_order",
            "is_system",
        ]
        read_only_fields = fields


class UserColorPreferenceSerializer(serializers.ModelSerializer):
    color_definition = ColorDefinitionSerializer(read_only=True)
    hex_value = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = UserColorPreference
        fields = [
            "id",
            "color_definition",
            "custom_hex",
            "custom_name",
            "display_order",
            "hex_value",
            "name",
            "created",
            "modified",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_hex_value(self, obj):
        if obj.custom_hex:
            return obj.custom_hex
        if obj.color_definition_id:
            return obj.color_definition.hex_value
        return ""

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj):
        if obj.custom_name:
            return obj.custom_name
        if obj.color_definition_id:
            return obj.color_definition.name
        return ""


class MergedColorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.IntegerField(required=False, allow_null=True)
    hex_value = serializers.CharField()
    name = serializers.CharField()
    display_order = serializers.IntegerField(
        help_text="System colors: fixed default_order (1–16). Custom colors: user sort order."
    )
    is_system = serializers.BooleanField()
    is_custom = serializers.BooleanField()


def _validate_optional_hex(value: str) -> str:
    if not value:
        return ""
    try:
        return normalize_color_code(value)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc)) from exc


class UserColorPreferenceCreateSerializer(serializers.ModelSerializer):
    color_definition_id = serializers.UUIDField(required=False, allow_null=True)
    custom_hex = serializers.CharField(required=False, allow_blank=True, default="")
    custom_name = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = UserColorPreference
        fields = [
            "color_definition_id",
            "custom_hex",
            "custom_name",
            "display_order",
        ]

    def validate_custom_hex(self, value):
        return _validate_optional_hex(value)

    def validate(self, attrs):
        if not attrs.get("color_definition_id") and not attrs.get("custom_hex"):
            raise serializers.ValidationError(
                "Either color_definition_id or custom_hex is required!"
            )
        if attrs.get("color_definition_id") and "display_order" in attrs:
            raise serializers.ValidationError(
                {"display_order": "System colors use fixed order; display_order applies to custom colors only!"}
            )
        return attrs

    def create(self, validated_data):
        color_definition_id = validated_data.pop("color_definition_id", None)
        if color_definition_id:
            validated_data.pop("display_order", None)
        return UserColorPreference.objects.create(
            user=self.context["request"].user,
            color_definition_id=color_definition_id,
            **validated_data,
        )


class UserColorPreferenceUpdateSerializer(serializers.ModelSerializer):
    custom_hex = serializers.CharField(required=False, allow_blank=True)
    custom_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    display_order = serializers.IntegerField(required=False, min_value=0)

    class Meta:
        model = UserColorPreference
        fields = ["custom_hex", "custom_name", "display_order"]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_custom_hex(self, value):
        return _validate_optional_hex(value)

    def validate(self, attrs):
        instance = self.instance
        if instance.color_definition_id and "display_order" in attrs:
            raise serializers.ValidationError(
                {"display_order": "System colors use fixed order; cannot reorder!"}
            )
        if not attrs:
            raise serializers.ValidationError("At least one field is required!")
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
