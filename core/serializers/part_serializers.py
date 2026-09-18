from rest_framework import serializers

from core.constant import PartStatusEnum
from core.models import Part
from core.serializers.fields import coerce_optional_string
from core.serializers.file_serializers import FileObjectSerializer
from core.serializers.source_document_serializers import SourceDocumentSerializer


class PartSerializer(serializers.ModelSerializer):
    preview_file = FileObjectSerializer(read_only=True)
    work_item_id = serializers.UUIDField(source="work_item.id", read_only=True)

    class Meta:
        model = Part
        fields = [
            "id",
            "source_document",
            "work_item_id",
            "sequence",
            "name",
            "status",
            "source_page",
            "source_bbox",
            "preview_file",
            "detected_metadata",
            "created_by",
            "updated_by",
            "created",
            "modified",
        ]
        read_only_fields = fields


class PartDetailSerializer(PartSerializer):
    source_document = SourceDocumentSerializer(read_only=True)


class PartWithStepsProgressSerializer(PartSerializer):
    total_steps = serializers.IntegerField(read_only=True)
    completed_steps = serializers.IntegerField(read_only=True)

    class Meta(PartSerializer.Meta):
        fields = PartSerializer.Meta.fields + ["total_steps", "completed_steps"]
        read_only_fields = fields


class WorkItemPartsListSerializer(serializers.Serializer):
    parts = PartSerializer(many=True, read_only=True)
    total_parts = serializers.IntegerField(read_only=True)
    completed_parts = serializers.IntegerField(read_only=True)


class UpdatePartSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        trim_whitespace=True,
        error_messages={
            "invalid": "Part name must be a string!",
            "max_length": "Part name cannot exceed 255 characters!",
        },
    )
    status = serializers.ChoiceField(
        choices=PartStatusEnum.choices,
        required=False,
        error_messages={
            "invalid_choice": "Invalid part status!",
            "null": "Invalid part status!",
        },
    )

    class Meta:
        model = Part
        fields = ["name", "status"]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_name(self, value):
        return coerce_optional_string(value)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        return instance
