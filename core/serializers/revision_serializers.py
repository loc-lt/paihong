import json

from rest_framework import serializers

from core.constant import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    DEFAULT_OUTPUT_ARTIFACT_ROLE,
    INTEGER_FIELD_MAX_VALUE,
    MAX_IMAGE_SIZE,
)
from core.models import PartStep, RevisionArtifact, StepRevision
from core.serializers.fields import coerce_optional_string
from core.serializers.file_serializers import FileObjectSerializer
from core.serializers.workflow_serializers import WorkflowStepDefinitionSerializer
from core.services.file_storage import get_file_url
from core.services.step_settings import unwrap_settings


class StepRevisionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = StepRevision
        fields = [
            "id",
            "revision_no",
            "revision_type",
            "settings_schema_version",
            "app_version",
            "created_by",
            "note",
            "created",
        ]
        read_only_fields = fields


class RevisionArtifactSerializer(serializers.ModelSerializer):
    file = FileObjectSerializer(read_only=True)

    class Meta:
        model = RevisionArtifact
        fields = [
            "id",
            "filename",
            "role",
            "sequence",
            "metadata",
            "file",
            "created",
        ]
        read_only_fields = fields


class StepRevisionSummaryWithFileUrlsSerializer(StepRevisionSummarySerializer):
    file_urls = serializers.SerializerMethodField()

    class Meta(StepRevisionSummarySerializer.Meta):
        fields = [*StepRevisionSummarySerializer.Meta.fields, "file_urls"]

    def get_file_urls(self, obj):
        if not obj:
            return []
        urls = []
        for artifact in obj.artifacts.all():
            file_object = artifact.file
            if file_object:
                urls.append(get_file_url(file_object.storage_key, file_object.storage_backend))
        return urls


class StepRevisionDetailSerializer(serializers.ModelSerializer):
    artifacts = RevisionArtifactSerializer(many=True, read_only=True)
    settings_meta = serializers.SerializerMethodField()

    class Meta:
        model = StepRevision
        fields = [
            "id",
            "part_step",
            "revision_no",
            "revision_type",
            "parent_revision",
            "settings",
            "settings_meta",
            "settings_schema_version",
            "app_version",
            "settings_hash",
            "created_by",
            "note",
            "artifacts",
            "created",
        ]
        read_only_fields = fields

    def get_settings_meta(self, obj):
        _data, meta = unwrap_settings(obj.settings)
        return meta

    def to_representation(self, instance):
        if instance is None:
            return None
        data = super().to_representation(instance)
        settings_data, _meta = unwrap_settings(instance.settings or {})
        data["settings"] = settings_data or {}
        return data


class PartStepSerializer(serializers.ModelSerializer):
    step = WorkflowStepDefinitionSerializer(read_only=True)
    latest_revision = StepRevisionSummarySerializer(read_only=True)
    official_revision = StepRevisionSummarySerializer(read_only=True)

    class Meta:
        model = PartStep
        fields = [
            "id",
            "part",
            "step",
            "status",
            "started_at",
            "completed_at",
            "latest_revision",
            "official_revision",
            "updated_by",
            "created",
            "modified",
        ]
        read_only_fields = fields


class PartStepDetailSerializer(PartStepSerializer):
    latest_revision = StepRevisionDetailSerializer(read_only=True)
    official_revision = StepRevisionDetailSerializer(read_only=True)


class PartStepWithRevisionFilesSerializer(PartStepSerializer):
    latest_revision = StepRevisionSummaryWithFileUrlsSerializer(read_only=True)
    official_revision = StepRevisionSummaryWithFileUrlsSerializer(read_only=True)


class PartStepsListSerializer(serializers.Serializer):
    steps = PartStepWithRevisionFilesSerializer(many=True, read_only=True)
    total_steps = serializers.IntegerField(read_only=True)
    completed_steps = serializers.IntegerField(read_only=True)


class FlexibleSettingsField(serializers.Field):
    """Accept settings from JSON body or multipart form (including empty values)."""

    default_error_messages = {
        "invalid": "Settings must be valid JSON!",
    }

    def to_internal_value(self, data):
        if data is None or data == "":
            return {}
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            stripped = data.strip()
            if stripped in ("", "null", "undefined"):
                return {}
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError(self.error_messages["invalid"]) from exc
            if parsed is None:
                return {}
            if not isinstance(parsed, dict):
                raise serializers.ValidationError(self.error_messages["invalid"])
            return parsed
        raise serializers.ValidationError(self.error_messages["invalid"])

    def to_representation(self, value):
        if not value:
            return {}
        if isinstance(value, dict):
            data, _meta = unwrap_settings(value)
            return data
        return value


def validate_revision_upload(uploaded_file) -> None:
    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError("File must be smaller than 50 MB!")
    filename = uploaded_file.name or ""
    if "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
        if extension not in ALLOWED_ARTIFACT_EXTENSIONS:
            allowed = ", ".join(ext.upper() for ext in ALLOWED_ARTIFACT_EXTENSIONS)
            raise serializers.ValidationError(f"File must be one of: {allowed}!")


class SaveStepRevisionSerializer(serializers.Serializer):
    settings = FlexibleSettingsField(required=False, default=dict)
    files = serializers.ListField(
        child=serializers.FileField(
            error_messages={
                "required": "Each file must be a valid upload!",
                "null": "Each file must be a valid upload!",
                "invalid": "Each file must be a valid upload!",
                "empty": "File cannot be empty!",
                "no_name": "Each file must be a valid upload!",
            },
        ),
        required=False,
        allow_empty=True,
        error_messages={
            "required": "Files must be a list!",
            "null": "Files must be a list!",
            "empty": "Files list cannot be empty when provided!",
            "not_a_list": "Files must be a list!",
            "invalid": "Files must be a list!",
        },
    )
    base_revision_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Invalid base revision ID format!",
            "null": "Invalid base revision ID format!",
        },
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "Note must be a string!",
        },
    )
    app_version = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=50,
        trim_whitespace=True,
        error_messages={
            "invalid": "App version must be a string!",
            "max_length": "App version cannot exceed 50 characters!",
        },
    )
    settings_schema_version = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=INTEGER_FIELD_MAX_VALUE,
        default=1,
        error_messages={
            "invalid": "Settings schema version must be an integer!",
            "min_value": "Settings schema version must be at least 1!",
            "max_value": "Settings schema version is too large!",
            "max_string_length": "Settings schema version is too large!",
        },
    )

    def _collect_uploaded_files(self, attrs):
        request = self.context.get("request")
        request_files = []
        if request:
            request_files.extend(request.FILES.getlist("files"))
            request_files.extend(request.FILES.getlist("artifact_files"))

        # Multipart (e.g. Swagger) may populate both serializer "files" and request.FILES.
        if request_files:
            return request_files
        return list(attrs.get("files") or [])

    def validate_app_version(self, value):
        return coerce_optional_string(value)

    def validate_settings_schema_version(self, value):
        if value is None:
            return 1
        return value

    def validate(self, attrs):
        files = self._collect_uploaded_files(attrs)
        for uploaded in files:
            validate_revision_upload(uploaded)
        attrs["files"] = files
        attrs["settings"] = attrs.get("settings") or {}
        return attrs

    def _build_artifacts(self):
        return [
            {
                "file": uploaded,
                "role": DEFAULT_OUTPUT_ARTIFACT_ROLE,
                "filename": uploaded.name or "",
                "sequence": index,
                "metadata": {},
            }
            for index, uploaded in enumerate(self.validated_data.get("files") or [])
        ]

    def create_revision(self, *, part_step, revision_type, mark_step_done=False):
        from core.services.step_revision import StepRevisionResult, create_step_revision

        result = create_step_revision(
            part_step=part_step,
            revision_type=revision_type,
            settings=self.validated_data.get("settings") or {},
            artifacts=self._build_artifacts(),
            user=self.context["request"].user,
            base_revision_id=self.validated_data.get("base_revision_id"),
            app_version=self.validated_data.get("app_version", ""),
            note=self.validated_data.get("note") or "",
            settings_schema_version=self.validated_data.get(
                "settings_schema_version", 1
            )
            or 1,
            mark_step_done=mark_step_done,
        )
        if isinstance(result, StepRevisionResult):
            return result
        return StepRevisionResult(revision=result, next_step_settings=None)


CreateRevisionSerializer = SaveStepRevisionSerializer


class RestoreRevisionSerializer(serializers.Serializer):
    base_revision_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": "Invalid base revision ID format!",
            "null": "Invalid base revision ID format!",
        },
    )

    def restore(self, *, revision):
        from core.services.step_revision import restore_revision

        return restore_revision(
            revision=revision,
            user=self.context["request"].user,
            base_revision_id=self.validated_data.get("base_revision_id"),
        )
