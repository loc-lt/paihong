from rest_framework import serializers


def _required_text(label: str, *, max_length: int) -> serializers.CharField:
    return serializers.CharField(
        max_length=max_length,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": f"{label} is required!",
            "blank": f"{label} cannot be empty!",
            "null": f"{label} is required!",
            "invalid": f"{label} must be a string!",
            "max_length": f"{label} cannot exceed {max_length} characters!",
        },
    )


def _required_revision_id(label: str) -> serializers.UUIDField:
    return serializers.UUIDField(
        error_messages={
            "required": f"{label} is required!",
            "null": f"{label} is required!",
            "invalid": f"{label} must be a revision id!",
        },
    )


def _optional_number(label: str) -> serializers.FloatField:
    return serializers.FloatField(
        required=False,
        allow_null=True,
        error_messages={
            "invalid": f"{label} must be a number!",
            "max_string_length": f"{label} is too large!",
            "overflow": f"{label} is too large!",
        },
    )


class AiServiceResponseSerializer(serializers.Serializer):
    """Shape returned by the AI service. This API forwards that body unchanged."""

    status = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    message = serializers.CharField(allow_blank=True, required=False)


class SmartSRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    svg_id = _required_revision_id("SVG revision id")
    wales_per_inch = _optional_number("Wales per inch")
    courses_per_cm = _optional_number("Courses per cm")
    courses_per_pixel = _optional_number("Courses per pixel")


class MergeImagesRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    image_ids = serializers.ListField(
        allow_empty=False,
        child=_required_revision_id("Image revision id"),
        error_messages={
            "required": "Image revision ids are required!",
            "null": "Image revision ids are required!",
            "not_a_list": "Image revision ids must be a list!",
            "invalid": "Image revision ids must be a list!",
            "empty": "Image revision ids cannot be empty!",
        },
    )
    background = serializers.ChoiceField(
        choices=["white", "black"],
        required=False,
        default="white",
        error_messages={
            "invalid_choice": "Invalid background!",
            "null": "Invalid background!",
        },
    )


class CreateFilesCRequestSerializer(serializers.Serializer):
    file_id = _required_revision_id("File revision id")
    product_code = _required_text("Product code", max_length=255)


class CreateFilePRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    l_id = _required_revision_id("Left revision id")
    r_id = _required_revision_id("Right revision id")
    l_f_id = _required_revision_id("Left rotated revision id")
    r_f_id = _required_revision_id("Right rotated revision id")
    wales_per_inch = _optional_number("Wales per inch")
    courses_per_cm = _optional_number("Courses per cm")
    courses_per_pixel = _optional_number("Courses per pixel")
