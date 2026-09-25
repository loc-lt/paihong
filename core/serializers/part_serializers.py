from rest_framework import serializers

from core.constant import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    MAX_IMAGE_SIZE,
    PartStatusEnum,
)
from core.models import Part
from core.serializers.fields import coerce_optional_string
from core.serializers.file_serializers import FileObjectSerializer
from core.serializers.revision_serializers import validate_revision_upload
from core.serializers.source_document_serializers import SourceDocumentSerializer
from core.services.file_storage import delete_file_object, store_uploaded_file


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
    preview = serializers.FileField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="Replace part preview/thumbnail image (PNG, JPG, JPEG, SVG).",
    )

    class Meta:
        model = Part
        fields = ["name", "status", "preview"]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_name(self, value):
        return coerce_optional_string(value)

    def validate_preview(self, value):
        if value is None:
            return None
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("Preview image must be smaller than 50 MB!")
        validate_revision_upload(value)
        extension = (value.name or "").rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_ARTIFACT_EXTENSIONS:
            allowed = ", ".join(ext.upper() for ext in ALLOWED_ARTIFACT_EXTENSIONS)
            raise serializers.ValidationError(f"Preview must be one of: {allowed}!")
        return value

    def update(self, instance, validated_data):
        user = self.context["request"].user
        preview = validated_data.pop("preview", serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if preview is not serializers.empty:
            if preview is None:
                if instance.preview_file_id:
                    old = instance.preview_file
                    delete_file_object(old)
                    old.delete()
                instance.preview_file = None
            else:
                if instance.preview_file_id:
                    old = instance.preview_file
                    delete_file_object(old)
                    old.delete()
                instance.preview_file = store_uploaded_file(preview, created_by=user)
        instance.updated_by = user
        instance.save()
        return instance
