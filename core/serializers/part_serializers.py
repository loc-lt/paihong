from rest_framework import serializers

from core.constant import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    MAX_IMAGE_SIZE,
    PartStatusEnum,
)
from core.models import Part, SourceDocument
from core.serializers.fields import coerce_optional_string
from core.serializers.file_serializers import FileObjectSerializer
from core.serializers.revision_serializers import validate_revision_upload
from core.serializers.source_document_serializers import SourceDocumentSerializer
from core.services.file_storage import delete_file_object_if_unreferenced, store_uploaded_file
from core.services.part_manage import create_manual_parts


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


def _validate_preview_upload(value):
    if value.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError("Preview image must be smaller than 50 MB!")
    validate_revision_upload(value)
    extension = (value.name or "").rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_ARTIFACT_EXTENSIONS:
        allowed = ", ".join(ext.upper() for ext in ALLOWED_ARTIFACT_EXTENSIONS)
        raise serializers.ValidationError(f"Preview must be one of: {allowed}!")
    return value


class BulkCreatePartSerializer(serializers.Serializer):
    source_document_id = serializers.PrimaryKeyRelatedField(
        queryset=SourceDocument.objects.all(),
        source="source_document",
        error_messages={
            "required": "Source document is required!",
            "null": "Source document is required!",
            "does_not_exist": "Source document not found!",
            "incorrect_type": "Invalid source document ID format!",
        },
    )
    previews = serializers.ListField(
        child=serializers.FileField(
            error_messages={
                "invalid": "Each preview must be a file!",
                "empty": "Preview image cannot be empty!",
                "no_name": "Each preview must be a file!",
            },
        ),
        allow_empty=False,
        help_text="One or more preview images (SVG recommended; PNG, JPG, JPEG also accepted).",
        error_messages={
            "required": "At least one preview image is required!",
            "null": "At least one preview image is required!",
            "empty": "At least one preview image is required!",
            "not_a_list": "Previews must be a list of files!",
            "invalid": "Previews must be a list of files!",
        },
    )

    def validate(self, attrs):
        previews = []
        for preview in attrs.get("previews") or []:
            previews.append(_validate_preview_upload(preview))
        attrs["previews"] = previews
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        items = [
            {"preview_file": store_uploaded_file(preview, created_by=user)}
            for preview in validated_data["previews"]
        ]
        return create_manual_parts(
            source_document=validated_data["source_document"],
            items=items,
            user=user,
        )


class BulkDeletePartSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(
            error_messages={"invalid": "Invalid part ID format!"},
        ),
        allow_empty=False,
        error_messages={
            "required": "Part IDs are required!",
            "null": "Part IDs are required!",
            "empty": "At least one part ID is required!",
            "not_a_list": "Part IDs must be a list!",
            "invalid": "Part IDs must be a list!",
        },
    )

    def validate_ids(self, value):
        unique_ids = list(dict.fromkeys(value))
        found = set(Part.objects.filter(pk__in=unique_ids).values_list("pk", flat=True))
        if any(part_id not in found for part_id in unique_ids):
            raise serializers.ValidationError("Part not found!")
        return unique_ids


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
        return _validate_preview_upload(value)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        preview = validated_data.pop("preview", serializers.empty)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        old_preview = None
        if preview is not serializers.empty:
            old_preview = instance.preview_file if instance.preview_file_id else None
            instance.preview_file = (
                store_uploaded_file(preview, created_by=user) if preview else None
            )
        instance.updated_by = user
        instance.save()
        if old_preview and old_preview.id != instance.preview_file_id:
            delete_file_object_if_unreferenced(old_preview)
        return instance
