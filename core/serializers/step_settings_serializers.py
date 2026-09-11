from rest_framework import serializers

from core.constant import INTEGER_FIELD_MAX_VALUE


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


class StepPickUpperSettingsSerializer(serializers.Serializer):
    selected_candidate = serializers.IntegerField(
        min_value=0,
        max_value=INTEGER_FIELD_MAX_VALUE,
        error_messages={
            "required": "Selected candidate is required!",
            "invalid": "Selected candidate must be an integer!",
            "null": "Selected candidate is required!",
            "min_value": "Selected candidate cannot be negative!",
            "max_value": "Selected candidate is too large!",
            "max_string_length": "Selected candidate is too large!",
        },
    )
    rotation = serializers.FloatField(
        error_messages={
            "required": "Rotation is required!",
            "invalid": "Rotation must be a number!",
            "null": "Rotation is required!",
        },
    )


class StepFixLinesByAnchorSettingsSerializer(serializers.Serializer):
    anchors = AnchorSerializer(
        many=True,
        error_messages={
            "required": "Anchors are required!",
            "null": "Anchors are required!",
            "empty": "At least one anchor is required!",
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
            "null": "Canvas height is required!",
            "min_value": "Canvas height cannot be negative!",
        },
    )


class OriginSerializer(serializers.Serializer):
    x = serializers.FloatField(
        error_messages={
            "required": "Origin X coordinate is required!",
            "invalid": "Origin X coordinate must be a number!",
            "null": "Origin X coordinate is required!",
        },
    )
    y = serializers.FloatField(
        error_messages={
            "required": "Origin Y coordinate is required!",
            "invalid": "Origin Y coordinate must be a number!",
            "null": "Origin Y coordinate is required!",
        },
    )


class StepCanvasFrameSettingsSerializer(serializers.Serializer):
    canvas = CanvasSerializer(
        error_messages={
            "required": "Canvas settings are required!",
            "null": "Canvas settings are required!",
        },
    )
    origin = OriginSerializer(
        error_messages={
            "required": "Origin settings are required!",
            "null": "Origin settings are required!",
        },
    )
    scale = serializers.FloatField(
        min_value=0,
        error_messages={
            "required": "Scale is required!",
            "invalid": "Scale must be a number!",
            "null": "Scale is required!",
            "min_value": "Scale cannot be negative!",
        },
    )


STEP_SETTINGS_SERIALIZER_MAP = {
    "PICK_UPPER": StepPickUpperSettingsSerializer,
    "FIX_LINES_BY_ANCHOR": StepFixLinesByAnchorSettingsSerializer,
    "CANVAS_FRAME_MEASURE": StepCanvasFrameSettingsSerializer,
}


def validate_step_settings(step_code: str, settings: dict, schema_key: str = "") -> dict:
    lookup_key = schema_key or step_code
    serializer_cls = STEP_SETTINGS_SERIALIZER_MAP.get(lookup_key)
    if not serializer_cls:
        serializer_cls = STEP_SETTINGS_SERIALIZER_MAP.get(step_code)
    if not serializer_cls:
        return settings or {}

    serializer = serializer_cls(data=settings or {})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
