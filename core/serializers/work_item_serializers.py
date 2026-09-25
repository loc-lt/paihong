from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.constant import WorkItemStatusEnum
from core.models import WorkItem, WorkflowTemplate
from core.serializers.fields import BoundedUUIDRelatedField, coerce_optional_string
from core.serializers.part_serializers import PartWithStepsProgressSerializer
from core.serializers.source_document_serializers import SourceDocumentSerializer
from core.services.part_workflow import get_default_workflow_template
from core.services.work_item_process import resolve_work_item_status


class WorkItemSerializer(serializers.ModelSerializer):
    workflow_template_id = serializers.UUIDField(
        source="workflow_template.id",
        read_only=True,
        allow_null=True,
    )
    parts_count = serializers.IntegerField(read_only=True)
    completed_parts = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = WorkItem
        fields = [
            "id",
            "item_code",
            "name",
            "status",
            "workflow_template_id",
            "parts_count",
            "completed_parts",
            "created_by",
            "updated_by",
            "created",
            "modified",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=WorkItemStatusEnum.choices))
    def get_status(self, obj):
        return resolve_work_item_status(obj)


class WorkItemItemCodeAvailabilitySerializer(serializers.Serializer):
    item_code = serializers.CharField(read_only=True)
    available = serializers.BooleanField(read_only=True)


class WorkItemDetailSerializer(WorkItemSerializer):
    source_documents = SourceDocumentSerializer(many=True, read_only=True)
    parts = serializers.SerializerMethodField()

    class Meta(WorkItemSerializer.Meta):
        fields = [
            field
            for field in WorkItemSerializer.Meta.fields
            if field not in {"parts_count", "completed_parts"}
        ] + ["source_documents", "parts"]
        read_only_fields = fields

    @extend_schema_field(PartWithStepsProgressSerializer(many=True))
    def get_parts(self, obj):
        parts = []
        for source_document in obj.source_documents.all():
            parts.extend(source_document.parts.all())
        return PartWithStepsProgressSerializer(parts, many=True).data


class UpdateWorkItemSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
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
        error_messages={
            "invalid_choice": "Invalid work item status!",
            "null": "Invalid work item status!",
        },
    )
    workflow_template_id = BoundedUUIDRelatedField(
        queryset=WorkflowTemplate.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        source="workflow_template",
        uuid_error_messages={
            "invalid": "Invalid workflow template ID format!",
        },
        error_messages={
            "does_not_exist": "Workflow template not found!",
            "incorrect_type": "Invalid workflow template ID format!",
        },
    )

    class Meta:
        model = WorkItem
        fields = ["name", "status", "workflow_template_id"]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_name(self, value):
        return coerce_optional_string(value)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        if "workflow_template" in validated_data:
            workflow_template = validated_data.pop("workflow_template")
            if workflow_template is None:
                instance.workflow_template = get_default_workflow_template()
            else:
                instance.workflow_template = workflow_template

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = user
        instance.save()
        return instance
