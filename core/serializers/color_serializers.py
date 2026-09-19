from rest_framework import serializers

from core.models import ColorDefinition, UserColorPreference


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

    def get_hex_value(self, obj):
        if obj.custom_hex:
            return obj.custom_hex
        if obj.color_definition_id:
            return obj.color_definition.hex_value
        return ""

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
    display_order = serializers.IntegerField()
    is_system = serializers.BooleanField()
    is_custom = serializers.BooleanField()


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

    def validate(self, attrs):
        if not attrs.get("color_definition_id") and not attrs.get("custom_hex"):
            raise serializers.ValidationError(
                "Either color_definition_id or custom_hex is required!"
            )
        return attrs

    def create(self, validated_data):
        color_definition_id = validated_data.pop("color_definition_id", None)
        return UserColorPreference.objects.create(
            user=self.context["request"].user,
            color_definition_id=color_definition_id,
            **validated_data,
        )
