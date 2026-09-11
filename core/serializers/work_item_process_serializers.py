from rest_framework import serializers

from core.constant import WorkItemStatusEnum
from core.models import WorkItem, WorkflowTemplate
from core.serializers.fields import BoundedUUIDRelatedField
from core.serializers.part_serializers import PartSerializer
from core.serializers.source_document_serializers import SourceDocumentSerializer
from core.serializers.work_item_serializers import WorkItemSerializer
from core.services.source_document import validate_source_upload
from core.services.part_workflow import get_default_workflow_template
from core.services.work_item_process import process_work_item


class ProcessWorkItemSerializer(serializers.Serializer):
    item_code = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Item code is required!",
            "blank": "Item code cannot be empty!",
            "null": "Item code is required!",
            "invalid": "Item code must be a string!",
            "max_length": "Item code cannot exceed 255 characters!",
        },
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        trim_whitespace=True,
        error_messages={
            "invalid": "Name must be a string!",
            "max_length": "Name cannot exceed 255 characters!",
        },
    )
    status = serializers.ChoiceField(
        choices=WorkItemStatusEnum.choices,
        required=False,
        default=WorkItemStatusEnum.NEW.value,
        error_messages={
            "invalid_choice": "Invalid work item status!",
            "null": "Invalid work item status!",
        },
    )
    workflow_template_id = BoundedUUIDRelatedField(
        queryset=WorkflowTemplate.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        uuid_error_messages={
            "invalid": "Invalid workflow template ID format!",
        },
        error_messages={
            "does_not_exist": "Workflow template not found!",
            "incorrect_type": "Invalid workflow template ID format!",
        },
    )
    files = serializers.ListField(
        child=serializers.FileField(
            error_messages={
                "invalid": "Each source file must be a valid upload!",
                "empty": "Source file cannot be empty!",
            },
        ),
        required=False,
        allow_empty=False,
        error_messages={
            "empty": "At least one source file is required!",
        },
    )

    def validate_item_code(self, value):
        item_code = value.strip()
        if WorkItem.objects.filter(item_code=item_code).exists():
            raise serializers.ValidationError("Item code already exists!")
        return item_code

    def validate(self, attrs):
        request = self.context["request"]
        files = attrs.get("files") or request.FILES.getlist("files")
        if not files:
            raise serializers.ValidationError(
                {"files": "At least one source file is required!"}
            )
        for uploaded in files:
            validate_source_upload(uploaded)
        attrs["files"] = files
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        workflow_template = validated_data.pop("workflow_template_id", None)
        if workflow_template is None:
            workflow_template = get_default_workflow_template()

        return process_work_item(
            user=user,
            item_code=validated_data["item_code"],
            name=validated_data.get("name", ""),
            status=validated_data.get("status", WorkItemStatusEnum.NEW.value),
            workflow_template=workflow_template,
            files=validated_data["files"],
        )


class ProcessWorkItemResultSerializer(serializers.Serializer):
    work_item = WorkItemSerializer()
    source_documents = SourceDocumentSerializer(many=True)
    parts = PartSerializer(many=True)
