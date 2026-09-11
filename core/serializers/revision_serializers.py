import json

from rest_framework import serializers

from core.constant import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    DEFAULT_OUTPUT_ARTIFACT_ROLE,
    INTEGER_FIELD_MAX_VALUE,
    MAX_IMAGE_SIZE,
)
from core.models import PartStep, RevisionArtifact, StepRevision
from core.serializers.file_serializers import FileObjectSerializer
from core.serializers.workflow_serializers import WorkflowStepDefinitionSerializer


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


class StepRevisionDetailSerializer(serializers.ModelSerializer):
    artifacts = RevisionArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = StepRevision
        fields = [
            "id",
            "part_step",
            "revision_no",
            "revision_type",
            "parent_revision",
            "settings",
            "settings_schema_version",
            "app_version",
            "settings_hash",
            "created_by",
            "note",
            "artifacts",
            "created",
        ]


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


class PartStepDetailSerializer(PartStepSerializer):
    latest_revision = StepRevisionDetailSerializer(read_only=True)
    official_revision = StepRevisionDetailSerializer(read_only=True)


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
    settings = serializers.JSONField(
        required=False,
        default=dict,
        error_messages={
            "invalid": "Settings must be valid JSON!",
        },
    )
    files = serializers.ListField(
        child=serializers.FileField(
            error_messages={
                "invalid": "Each file must be a valid upload!",
                "empty": "File cannot be empty!",
            },
        ),
        required=False,
        error_messages={
            "empty": "Files list cannot be empty when provided!",
        },
    )
    base_revision_id = serializers.UUIDField(
        required=False,
        error_messages={
            "invalid": "Invalid base revision ID format!",
        },
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "Note must be a string!",
        },
    )
    app_version = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        trim_whitespace=True,
        error_messages={
            "invalid": "App version must be a string!",
            "max_length": "App version cannot exceed 50 characters!",
        },
    )
    settings_schema_version = serializers.IntegerField(
        required=False,
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

    def _parse_settings(self, settings):
        if settings in (None, ""):
            return {}
        if isinstance(settings, str):
            try:
                return json.loads(settings)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError(
                    {"settings": "Settings must be valid JSON!"}
                ) from exc
        if isinstance(settings, dict):
            return settings
        raise serializers.ValidationError({"settings": "Settings must be valid JSON!"})

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

    def validate(self, attrs):
        files = self._collect_uploaded_files(attrs)
        for uploaded in files:
            validate_revision_upload(uploaded)
        attrs["files"] = files
        attrs["settings"] = self._parse_settings(attrs.get("settings"))
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
        from core.services.step_revision import create_step_revision

        return create_step_revision(
            part_step=part_step,
            revision_type=revision_type,
            settings=self.validated_data.get("settings") or {},
            artifacts=self._build_artifacts(),
            user=self.context["request"].user,
            base_revision_id=self.validated_data.get("base_revision_id"),
            app_version=self.validated_data.get("app_version", ""),
            note=self.validated_data.get("note", ""),
            settings_schema_version=self.validated_data.get(
                "settings_schema_version", 1
            ),
            mark_step_done=mark_step_done,
        )


CreateRevisionSerializer = SaveStepRevisionSerializer


class RestoreRevisionSerializer(serializers.Serializer):
    base_revision_id = serializers.UUIDField(
        required=False,
        error_messages={
            "invalid": "Invalid base revision ID format!",
        },
    )

    def restore(self, *, revision):
        from core.services.step_revision import restore_revision

        return restore_revision(
            revision=revision,
            user=self.context["request"].user,
            base_revision_id=self.validated_data.get("base_revision_id"),
        )
