from rest_framework import serializers

from core.constant import INTEGER_FIELD_MAX_VALUE


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
    list_image_ids = serializers.ListField(
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
    product_code = _required_text("Product code", max_length=255)
    image_id = _required_revision_id("Image revision id")


class CreateFilePRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    l_id = _required_revision_id("Left revision id")
    r_id = _required_revision_id("Right revision id")
    l_f_id = _required_revision_id("Left rotated revision id")
    r_f_id = _required_revision_id("Right rotated revision id")
    wales_per_inch = _optional_number("Wales per inch")
    courses_per_cm = _optional_number("Courses per cm")
    courses_per_pixel = _optional_number("Courses per pixel")


class AiUrlPathProductCodeSerializer(serializers.Serializer):
    """FE passes the file URL directly; BE forwards it to AI unchanged."""

    url_path = _required_text("URL path", max_length=2000)
    product_code = _required_text("Product code", max_length=255)


class AiUrlSvgProductCodeSerializer(serializers.Serializer):
    """FE passes the SVG URL directly; BE forwards it to AI unchanged."""

    url_svg = _required_text("SVG URL", max_length=2000)
    product_code = _required_text("Product code", max_length=255)


class CreateTrainDbRequestSerializer(serializers.Serializer):
    url_svg = _required_text("SVG URL", max_length=2000)
    index_list = serializers.ListField(
        allow_empty=False,
        child=serializers.IntegerField(
            min_value=0,
            max_value=INTEGER_FIELD_MAX_VALUE,
            error_messages={
                "invalid": "Each index must be an integer!",
                "min_value": "Each index must be at least 0!",
                "max_value": "Each index is too large!",
                "max_string_length": "Each index is too large!",
                "null": "Each index must be an integer!",
            },
        ),
        error_messages={
            "required": "Index list is required!",
            "null": "Index list is required!",
            "not_a_list": "Index list must be a list!",
            "invalid": "Index list must be a list!",
            "empty": "Index list cannot be empty!",
        },
    )
    type = _required_text("Type", max_length=255)


class CreateTrainDbAnchorRequestSerializer(serializers.Serializer):
    url_svg = _required_text("SVG URL", max_length=2000)
    index_list = serializers.ListField(
        allow_empty=False,
        child=serializers.ListField(
            child=serializers.IntegerField(
                min_value=0,
                max_value=INTEGER_FIELD_MAX_VALUE,
                error_messages={
                    "invalid": "Each anchor index must be an integer!",
                    "min_value": "Each anchor index must be at least 0!",
                    "max_value": "Each anchor index is too large!",
                    "max_string_length": "Each anchor index is too large!",
                    "null": "Each anchor index must be an integer!",
                },
            ),
            min_length=2,
            max_length=2,
            error_messages={
                "not_a_list": "Each anchor index must be a [path_index, point_index] pair!",
                "invalid": "Each anchor index must be a [path_index, point_index] pair!",
                "empty": "Each anchor index must be a [path_index, point_index] pair!",
                "min_length": "Each anchor index must be a [path_index, point_index] pair!",
                "max_length": "Each anchor index must be a [path_index, point_index] pair!",
                "null": "Each anchor index must be a [path_index, point_index] pair!",
            },
        ),
        error_messages={
            "required": "Index list is required!",
            "null": "Index list is required!",
            "not_a_list": "Index list must be a list!",
            "invalid": "Index list must be a list!",
            "empty": "Index list cannot be empty!",
        },
    )


class CreateFileFcRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    count = serializers.IntegerField(
        min_value=0,
        max_value=INTEGER_FIELD_MAX_VALUE,
        error_messages={
            "required": "Count is required!",
            "null": "Count is required!",
            "invalid": "Count must be an integer!",
            "min_value": "Count must be at least 0!",
            "max_value": "Count is too large!",
            "max_string_length": "Count is too large!",
        },
    )
    image_id = _required_revision_id("Image revision id")
    type_machine = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        trim_whitespace=True,
        error_messages={
            "invalid": "Machine type must be a string!",
            "max_length": "Machine type cannot exceed 255 characters!",
        },
    )

    def validate_type_machine(self, value):
        if value is None:
            return None
        return value


def _optional_int(label: str) -> serializers.IntegerField:
    return serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=-INTEGER_FIELD_MAX_VALUE,
        max_value=INTEGER_FIELD_MAX_VALUE,
        error_messages={
            "invalid": f"{label} must be an integer!",
            "min_value": f"{label} is too small!",
            "max_value": f"{label} is too large!",
            "max_string_length": f"{label} is too large!",
        },
    )


def _optional_text(label: str) -> serializers.CharField:
    return serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        trim_whitespace=True,
        error_messages={
            "invalid": f"{label} must be a string!",
            "max_length": f"{label} cannot exceed 255 characters!",
        },
    )


def _optional_bool(label: str, *, default=False) -> serializers.BooleanField:
    return serializers.BooleanField(
        required=False,
        default=default,
        error_messages={
            "invalid": f"{label} must be true or false!",
            "null": f"{label} must be true or false!",
        },
    )


class AutoJobRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    image_id = _required_revision_id("Image revision id")
    type_machine = _optional_text("Machine type")
    number_jackquard = _optional_int("Number jackquard")


class CombineFcRequestSerializer(serializers.Serializer):
    product_code = _required_text("Product code", max_length=255)
    ff_id = _required_revision_id("FF revision id")
    fb_id = _required_revision_id("FB revision id")
    ff_has_hole = _optional_bool("FF has hole")
    fb_has_hole = _optional_bool("FB has hole")


class ShiftOddRowsRequestSerializer(serializers.Serializer):
    image_id = _required_revision_id("Image revision id")
    value = serializers.IntegerField(
        min_value=-INTEGER_FIELD_MAX_VALUE,
        max_value=INTEGER_FIELD_MAX_VALUE,
        error_messages={
            "required": "Shift value is required!",
            "null": "Shift value is required!",
            "invalid": "Shift value must be an integer!",
            "min_value": "Shift value is too small!",
            "max_value": "Shift value is too large!",
            "max_string_length": "Shift value is too large!",
        },
    )


class CreateKmoRequestSerializer(serializers.Serializer):
    image_id = _required_revision_id("Image revision id")
    name_machine = _optional_text("Machine name")
    gauge = _optional_int("Gauge")
    width = _optional_int("Width")
    rt = _optional_int("RT")
    product_code = _optional_text("Product code")
    course_per_pixel = _optional_int("Course per pixel")
    kmo_has_valve_chain = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=False,
        error_messages={
            "invalid": "KMO has valve chain must be true or false!",
        },
    )
