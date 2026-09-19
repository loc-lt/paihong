from rest_framework import serializers

from core.constant import INTEGER_FIELD_MAX_VALUE
from core.services.step_settings import normalize_incoming_settings


class AnchorSerializer(serializers.Serializer):
    x = serializers.FloatField(
        error_messages={
            "required": "Anchor X coordinate is required!",
            "invalid": "Anchor X coordinate must be a number!",
            "null": "Anchor X coordinate is required!",
        },
    )
    y = serializers.FloatField(
        error_messages={
            "required": "Anchor Y coordinate is required!",
            "invalid": "Anchor Y coordinate must be a number!",
            "null": "Anchor Y coordinate is required!",
        },
    )


class BboxSerializer(serializers.Serializer):
    x = serializers.FloatField(min_value=0)
    y = serializers.FloatField(min_value=0)
    w = serializers.FloatField(min_value=0)
    h = serializers.FloatField(min_value=0)


class PickUpperCandidateSerializer(serializers.Serializer):
    index = serializers.IntegerField(min_value=0, max_value=INTEGER_FIELD_MAX_VALUE)
    med = serializers.BooleanField(required=False, default=False)
    lat = serializers.BooleanField(required=False, default=False)
    size = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    width_mm = serializers.FloatField(required=False, allow_null=True, min_value=0)
    height_mm = serializers.FloatField(required=False, allow_null=True, min_value=0)
    label = serializers.CharField(required=False, allow_blank=True, default="")
    side = serializers.CharField(required=False, allow_blank=True, default="")
    variant = serializers.CharField(required=False, allow_blank=True, default="")
    size_class = serializers.CharField(required=False, allow_blank=True, default="")
    suggested_rotation_deg = serializers.FloatField(required=False, allow_null=True)
    preview_artifact_id = serializers.UUIDField(required=False, allow_null=True)
    bbox = BboxSerializer(required=False)


class StepPickUpperSettingsSerializer(serializers.Serializer):
    selected_candidate_index = serializers.IntegerField(
        min_value=0,
        max_value=INTEGER_FIELD_MAX_VALUE,
        error_messages={
            "required": "Selected candidate index is required!",
            "invalid": "Selected candidate index must be an integer!",
            "null": "Selected candidate index is required!",
            "min_value": "Selected candidate index cannot be negative!",
            "max_value": "Selected candidate index is too large!",
        },
    )
    rotation = serializers.FloatField(
        error_messages={
            "required": "Rotation is required!",
            "invalid": "Rotation must be a number!",
            "null": "Rotation is required!",
        },
    )
    candidates = PickUpperCandidateSerializer(many=True, required=False, default=list)


class StepFixLinesByAnchorSettingsSerializer(serializers.Serializer):
    anchors = AnchorSerializer(
        many=True,
        allow_empty=False,
        error_messages={
            "required": "Anchors are required!",
            "null": "Anchors are required!",
            "empty": "At least one anchor is required!",
            "not_a_list": "Anchors must be a list!",
            "invalid": "Anchors must be a list!",
        },
    )
    snap_distance = serializers.FloatField(
        min_value=0,
        error_messages={
            "required": "Snap distance is required!",
            "invalid": "Snap distance must be a number!",
            "null": "Snap distance is required!",
            "min_value": "Snap distance cannot be negative!",
        },
    )
    tolerance = serializers.FloatField(
        min_value=0,
        error_messages={
            "required": "Tolerance is required!",
            "invalid": "Tolerance must be a number!",
            "null": "Tolerance is required!",
            "min_value": "Tolerance cannot be negative!",
        },
    )


class LayerAssignmentSerializer(serializers.Serializer):
    color = serializers.CharField(required=False, allow_blank=True, default="")
    line_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )


class ManualOverrideSerializer(serializers.Serializer):
    line_id = serializers.CharField()
    layer = serializers.CharField()


class StepCheckColorsSettingsSerializer(serializers.Serializer):
    layers = serializers.JSONField(required=False, default=dict)
    manual_overrides = ManualOverrideSerializer(many=True, required=False, default=list)
    frame_expansion_mm = serializers.FloatField(required=False, default=0, min_value=0)
    corner_type = serializers.CharField(required=False, default="sharp")
    corner_limit = serializers.IntegerField(required=False, default=4, min_value=0)


class CanvasSerializer(serializers.Serializer):
    width_mm = serializers.FloatField(
        min_value=0,
        error_messages={
            "required": "Canvas width is required!",
            "invalid": "Canvas width must be a number!",
            "null": "Canvas width is required!",
            "min_value": "Canvas width cannot be negative!",
        },
    )
    height_mm = serializers.FloatField(
        min_value=0,
        error_messages={
            "required": "Canvas height is required!",
            "invalid": "Canvas height must be a number!",
            "null": "Canvas height cannot be negative!",
            "min_value": "Canvas height cannot be negative!",
        },
    )


class OriginSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()


class CanvasBasisSerializer(serializers.Serializer):
    outer_contour_line_count = serializers.IntegerField(required=False, default=0, min_value=0)
    measured_line_count = serializers.IntegerField(required=False, default=0, min_value=0)
    center_cross_included = serializers.BooleanField(required=False, default=False)


class StepCanvasFrameSettingsSerializer(serializers.Serializer):
    canvas = CanvasSerializer()
    origin = OriginSerializer()
    scale = serializers.FloatField(min_value=0)
    basis = CanvasBasisSerializer(required=False)


class GridPixelsSerializer(serializers.Serializer):
    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)


class SourceMeasurementsSerializer(serializers.Serializer):
    width = serializers.FloatField(min_value=0)
    height = serializers.FloatField(min_value=0)


class StepEnterSpecsSettingsSerializer(serializers.Serializer):
    needle_density = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "Needle density is required!",
            "invalid": "Needle density must be an integer!",
            "null": "Needle density is required!",
            "min_value": "Needle density must be at least 1!",
        },
    )
    cos_number = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "Cos number is required!",
            "invalid": "Cos number must be an integer!",
            "null": "Cos number is required!",
            "min_value": "Cos number must be at least 1!",
        },
    )
    course_per_pixel = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "Course per pixel is required!",
            "invalid": "Course per pixel must be an integer!",
            "null": "Course per pixel is required!",
            "min_value": "Course per pixel must be at least 1!",
        },
    )
    grid_pixels = GridPixelsSerializer(required=False)
    source_measurements_mm = SourceMeasurementsSerializer(required=False)


class StepBuildGridSettingsSerializer(serializers.Serializer):
    grid = GridPixelsSerializer()
    conversion = serializers.DictField(required=False, default=dict)
    grid_snapshot_id = serializers.UUIDField(required=False, allow_null=True)


class StepStartDesigningSettingsSerializer(serializers.Serializer):
    active_file_type = serializers.CharField(required=False, default="S1")
    progress = serializers.DictField(required=False, default=dict)


# Schemas kept for reference/docs; validation disabled — settings are stored as JSON pass-through.
STEP_SETTINGS_SERIALIZER_MAP: dict[str, type[serializers.Serializer]] = {}


def validate_step_settings(
    step_code: str,
    settings: dict,
    schema_key: str = "",
    *,
    default_source: str = "manual",
) -> dict:
    del step_code, schema_key
    return normalize_incoming_settings(settings, default_source=default_source)
