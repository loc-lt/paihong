from django.db import transaction
from rest_framework import serializers

from core.constant import INTEGER_FIELD_MAX_VALUE, POSITIVE_SMALL_INTEGER_MAX_VALUE
from core.models import TemplateStep, WorkflowStepDefinition, WorkflowTemplate
from core.serializers.fields import BoundedPrimaryKeyRelatedField


class WorkflowStepDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStepDefinition
        fields = [
            "id",
            "code",
            "sequence",
            "name",
            "description",
            "version",
            "is_active",
            "settings_schema_key",
        ]


class TemplateStepSerializer(serializers.ModelSerializer):
    step = BoundedPrimaryKeyRelatedField(
        queryset=WorkflowStepDefinition.objects.filter(is_active=True),
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        pk_error_messages={
            "invalid": "Workflow step must be an integer ID!",
            "min_value": "Workflow step ID must be a positive integer!",
            "max_value": "Workflow step ID is too large!",
            "max_string_length": "Workflow step ID is too large!",
        },
        error_messages={
            "does_not_exist": "Workflow step not found!",
            "incorrect_type": "Workflow step must be an integer ID!",
        },
    )
    step_code = serializers.CharField(source="step.code", read_only=True)
    step_name = serializers.CharField(source="step.name", read_only=True)

    class Meta:
        model = TemplateStep
        fields = [
            "id",
            "step",
            "step_code",
            "step_name",
            "sequence",
            "is_required",
            "settings_schema_version",
        ]
        read_only_fields = ["id", "step_code", "step_name"]


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    template_steps = TemplateStepSerializer(many=True, read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "is_default",
            "template_steps",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]


class TemplateStepInputSerializer(serializers.Serializer):
    step = BoundedPrimaryKeyRelatedField(
        queryset=WorkflowStepDefinition.objects.filter(is_active=True),
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        pk_error_messages={
            "invalid": "Workflow step must be an integer ID!",
            "min_value": "Workflow step ID must be a positive integer!",
            "max_value": "Workflow step ID is too large!",
            "max_string_length": "Workflow step ID is too large!",
        },
        error_messages={
            "does_not_exist": "Workflow step not found!",
            "incorrect_type": "Workflow step must be an integer ID!",
        },
    )
    sequence = serializers.IntegerField(
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        error_messages={
            "required": "Template step sequence is required!",
            "invalid": "Template step sequence must be an integer!",
            "null": "Template step sequence is required!",
            "min_value": "Template step sequence must be at least 1!",
            "max_value": "Template step sequence is too large!",
            "max_string_length": "Template step sequence is too large!",
        },
    )
    is_required = serializers.BooleanField(
        required=False,
        default=True,
        error_messages={
            "invalid": "Is required must be true or false!",
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


class CreateWorkflowTemplateSerializer(serializers.ModelSerializer):
    code = serializers.CharField(
        max_length=100,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Template code is required!",
            "blank": "Template code cannot be empty!",
            "null": "Template code is required!",
            "invalid": "Template code must be a string!",
            "max_length": "Template code cannot exceed 100 characters!",
        },
    )
    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Template name is required!",
            "blank": "Template name cannot be empty!",
            "null": "Template name is required!",
            "invalid": "Template name must be a string!",
            "max_length": "Template name cannot exceed 255 characters!",
        },
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "Description must be a string!",
        },
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        error_messages={
            "invalid": "Is active must be true or false!",
        },
    )
    is_default = serializers.BooleanField(
        required=False,
        default=False,
        error_messages={
            "invalid": "Is default must be true or false!",
        },
    )
    template_steps = TemplateStepInputSerializer(
        many=True,
        required=True,
        error_messages={
            "required": "Template steps are required!",
            "null": "Template steps are required!",
            "empty": "At least one template step is required!",
        },
    )

    class Meta:
        model = WorkflowTemplate
        fields = [
            "code",
            "name",
            "description",
            "is_active",
            "is_default",
            "template_steps",
        ]

    def validate_code(self, value):
        code = value.strip().upper()
        if not code:
            raise serializers.ValidationError("Template code cannot be empty!")
        return code

    def validate_template_steps(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one template step is required!"
            )
        sequences = [item["sequence"] for item in value]
        if len(sequences) != len(set(sequences)):
            raise serializers.ValidationError(
                "Template step sequence must be unique!"
            )
        step_ids = [item["step"].id for item in value]
        if len(step_ids) != len(set(step_ids)):
            raise serializers.ValidationError(
                "Duplicate workflow step in template!"
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        steps_data = validated_data.pop("template_steps")
        if validated_data.get("is_default"):
            WorkflowTemplate.objects.filter(is_default=True).update(is_default=False)

        template = WorkflowTemplate.objects.create(**validated_data)
        for step_data in steps_data:
            TemplateStep.objects.create(template=template, **step_data)
        return template


class UpdateWorkflowTemplateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=255,
        trim_whitespace=True,
        error_messages={
            "blank": "Template name cannot be empty!",
            "null": "Template name cannot be empty!",
            "invalid": "Template name must be a string!",
            "max_length": "Template name cannot exceed 255 characters!",
        },
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "Description must be a string!",
        },
    )
    is_active = serializers.BooleanField(
        required=False,
        error_messages={
            "invalid": "Is active must be true or false!",
        },
    )
    is_default = serializers.BooleanField(
        required=False,
        error_messages={
            "invalid": "Is default must be true or false!",
        },
    )
    template_steps = TemplateStepInputSerializer(many=True, required=False)

    class Meta:
        model = WorkflowTemplate
        fields = [
            "name",
            "description",
            "is_active",
            "is_default",
            "template_steps",
        ]

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super().__init__(*args, **kwargs)

    def validate_template_steps(self, value):
        if value is not None and not value:
            raise serializers.ValidationError(
                "At least one template step is required!"
            )
        if value:
            sequences = [item["sequence"] for item in value]
            if len(sequences) != len(set(sequences)):
                raise serializers.ValidationError(
                    "Template step sequence must be unique!"
                )
            step_ids = [item["step"].id for item in value]
            if len(step_ids) != len(set(step_ids)):
                raise serializers.ValidationError(
                    "Duplicate workflow step in template!"
                )
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        steps_data = validated_data.pop("template_steps", None)
        if validated_data.get("is_default"):
            WorkflowTemplate.objects.filter(is_default=True).exclude(
                id=instance.id
            ).update(is_default=False)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if steps_data is not None:
            instance.template_steps.all().delete()
            for step_data in steps_data:
                TemplateStep.objects.create(template=instance, **step_data)

        return instance


class WorkflowStepDefinitionWriteSerializer(serializers.ModelSerializer):
    code = serializers.CharField(
        max_length=100,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Step code is required!",
            "blank": "Step code cannot be empty!",
            "null": "Step code is required!",
            "invalid": "Step code must be a string!",
            "max_length": "Step code cannot exceed 100 characters!",
        },
    )
    sequence = serializers.IntegerField(
        min_value=1,
        max_value=POSITIVE_SMALL_INTEGER_MAX_VALUE,
        error_messages={
            "required": "Step sequence is required!",
            "invalid": "Step sequence must be an integer!",
            "null": "Step sequence is required!",
            "min_value": "Step sequence must be at least 1!",
            "max_value": "Step sequence is too large!",
            "max_string_length": "Step sequence is too large!",
        },
    )
    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "Step name is required!",
            "blank": "Step name cannot be empty!",
            "null": "Step name is required!",
            "invalid": "Step name must be a string!",
            "max_length": "Step name cannot exceed 255 characters!",
        },
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        error_messages={
            "invalid": "Description must be a string!",
        },
    )
    version = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=INTEGER_FIELD_MAX_VALUE,
        default=1,
        error_messages={
            "invalid": "Version must be an integer!",
            "min_value": "Version must be at least 1!",
            "max_value": "Version is too large!",
            "max_string_length": "Version is too large!",
        },
    )
    is_active = serializers.BooleanField(
        required=False,
        default=True,
        error_messages={
            "invalid": "Is active must be true or false!",
        },
    )
    settings_schema_key = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        trim_whitespace=True,
        error_messages={
            "invalid": "Settings schema key must be a string!",
            "max_length": "Settings schema key cannot exceed 100 characters!",
        },
    )

    class Meta:
        model = WorkflowStepDefinition
        fields = [
            "code",
            "sequence",
            "name",
            "description",
            "version",
            "is_active",
            "settings_schema_key",
        ]

    def validate_code(self, value):
        return value.strip().upper()
