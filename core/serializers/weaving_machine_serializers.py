from decimal import Decimal

from rest_framework import serializers

from core.constant import INTEGER_FIELD_MAX_VALUE, JacquardEnum, WeavingMachineTypeEnum
from core.models import WeavingMachine, WeavingMachineBar, WeavingMachineSpec

_INT_MAX = INTEGER_FIELD_MAX_VALUE
_DECIMAL_MAX = Decimal("999999.99")


def _int_errors(label, *, min_value, optional=False):
    errors = {
        "invalid": f"{label} must be an integer!",
        "min_value": f"{label} must be at least {min_value}!",
        "max_value": f"{label} is too large!",
        "max_string_length": f"{label} is too large!",
    }
    if optional:
        errors["null"] = f"{label} must be an integer!"
    else:
        errors["required"] = f"{label} is required!"
        errors["null"] = f"{label} is required!"
    return errors


def _decimal_errors(label, *, optional=False):
    errors = {
        "invalid": f"{label} must be a number!",
        "min_value": f"{label} must be at least 0!",
        "max_value": f"{label} is too large!",
        "max_digits": f"{label} is too large!",
        "max_decimal_places": f"{label} has too many decimal places!",
        "max_whole_digits": f"{label} is too large!",
        "max_string_length": f"{label} is too large!",
    }
    if optional:
        errors["null"] = f"{label} must be a number!"
    else:
        errors["required"] = f"{label} is required!"
        errors["null"] = f"{label} is required!"
    return errors


def required_int(label, *, min_value=0):
    return serializers.IntegerField(
        min_value=min_value,
        max_value=_INT_MAX,
        error_messages=_int_errors(label, min_value=min_value),
    )


def optional_int(label, *, min_value=0):
    return serializers.IntegerField(
        required=False,
        min_value=min_value,
        max_value=_INT_MAX,
        error_messages=_int_errors(label, min_value=min_value, optional=True),
    )


def required_decimal(label):
    return serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=_DECIMAL_MAX,
        error_messages=_decimal_errors(label),
    )


def optional_decimal(label):
    return serializers.DecimalField(
        required=False,
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=_DECIMAL_MAX,
        error_messages=_decimal_errors(label, optional=True),
    )


class _BarCodeField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("trim_whitespace", True)
        kwargs.setdefault("allow_blank", False)
        kwargs.setdefault(
            "error_messages",
            {
                "required": "Bar code is required!",
                "blank": "Bar code cannot be empty!",
                "null": "Bar code is required!",
                "invalid": "Bar code must be a string!",
                "max_length": "Bar code cannot exceed 20 characters!",
            },
        )
        super().__init__(**kwargs)


class WeavingMachineBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeavingMachineBar
        fields = [
            "id",
            "machine",
            "bar_no",
            "bar_code",
            "zul_max_kg",
            "max_versatzsprung",
            "max_ueberlegungssprung",
            "ns",
            "created",
            "modified",
        ]
        read_only_fields = fields


class WeavingMachineSpecSerializer(serializers.ModelSerializer):
    machine_name = serializers.CharField(source="machine.name", read_only=True)

    class Meta:
        model = WeavingMachineSpec
        fields = [
            "id",
            "machine",
            "machine_name",
            "needles_per_inch",
            "width",
            "created",
            "modified",
        ]
        read_only_fields = fields


class WeavingMachineSerializer(serializers.ModelSerializer):
    specs = WeavingMachineSpecSerializer(many=True, read_only=True)
    bars = WeavingMachineBarSerializer(many=True, read_only=True)

    class Meta:
        model = WeavingMachine
        fields = [
            "id",
            "name",
            "type",
            "jacquard",
            "max_bars",
            "specs",
            "bars",
            "created",
            "modified",
        ]
        read_only_fields = fields


class WeavingMachineSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeavingMachine
        fields = ["id", "name", "type", "jacquard", "max_bars", "created", "modified"]
        read_only_fields = fields


class BarWriteSerializer(serializers.Serializer):
    bar_no = required_int("Bar number", min_value=1)
    bar_code = _BarCodeField()
    zul_max_kg = optional_decimal("zul_max_kg")
    max_versatzsprung = optional_int("max_versatzsprung")
    max_ueberlegungssprung = optional_int("max_ueberlegungssprung")
    ns = optional_int("NS")

    def create(self, validated_data):
        from core.services.weaving_machine import create_bar

        return create_bar(self.context["machine"], **validated_data)


class BarUpdateSerializer(BarWriteSerializer):
    bar_no = optional_int("Bar number", min_value=1)
    bar_code = _BarCodeField(required=False)

    def update(self, instance, validated_data):
        from core.services.weaving_machine import update_bar

        return update_bar(instance, **validated_data)


class MachineWriteSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
        error_messages={
            "required": "Machine name is required!",
            "blank": "Machine name cannot be empty!",
            "null": "Machine name is required!",
            "invalid": "Machine name must be a string!",
            "max_length": "Machine name cannot exceed 100 characters!",
        },
    )
    type = serializers.ChoiceField(
        choices=WeavingMachineTypeEnum.choices,
        error_messages={
            "required": "Machine type is required!",
            "null": "Machine type is required!",
            "invalid_choice": "Machine type must be Single or Double!",
        },
    )
    jacquard = serializers.ChoiceField(
        choices=JacquardEnum.choices,
        error_messages={
            "required": "Jacquard is required!",
            "null": "Jacquard is required!",
            "invalid_choice": "Jacquard must be 1 or 2!",
        },
    )
    max_bars = optional_int("Max bars")
    bars = serializers.ListField(
        child=BarWriteSerializer(),
        required=False,
        allow_empty=True,
        error_messages={
            "not_a_list": "Bars must be a list!",
            "invalid": "Bars must be a list!",
            "null": "Bars must be a list!",
        },
    )

    def create(self, validated_data):
        from core.services.weaving_machine import create_machine

        return create_machine(
            name=validated_data["name"],
            type=validated_data["type"],
            jacquard=validated_data["jacquard"],
            max_bars=validated_data.get("max_bars", 0),
            bars=validated_data.get("bars"),
        )


class MachineUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        max_length=100,
        trim_whitespace=True,
        allow_blank=False,
        error_messages={
            "blank": "Machine name cannot be empty!",
            "null": "Machine name must be a string!",
            "invalid": "Machine name must be a string!",
            "max_length": "Machine name cannot exceed 100 characters!",
        },
    )
    type = serializers.ChoiceField(
        choices=WeavingMachineTypeEnum.choices,
        required=False,
        error_messages={
            "null": "Machine type must be Single or Double!",
            "invalid_choice": "Machine type must be Single or Double!",
        },
    )
    jacquard = serializers.ChoiceField(
        choices=JacquardEnum.choices,
        required=False,
        error_messages={
            "null": "Jacquard must be 1 or 2!",
            "invalid_choice": "Jacquard must be 1 or 2!",
        },
    )
    max_bars = optional_int("Max bars")
    bars = serializers.ListField(
        child=BarWriteSerializer(),
        required=False,
        allow_empty=True,
        error_messages={
            "not_a_list": "Bars must be a list!",
            "invalid": "Bars must be a list!",
            "null": "Bars must be a list!",
        },
    )

    def update(self, instance, validated_data):
        from core.services.weaving_machine import update_machine

        bars = validated_data.pop("bars", serializers.empty)
        kwargs = {}
        if bars is not serializers.empty:
            kwargs["bars"] = bars
        return update_machine(
            instance,
            name=validated_data.get("name"),
            type=validated_data.get("type"),
            jacquard=validated_data.get("jacquard"),
            max_bars=validated_data.get("max_bars"),
            **kwargs,
        )


class SpecWriteSerializer(serializers.Serializer):
    needles_per_inch = required_decimal("Gauge (n/inch)")
    width = required_decimal("Machine width")

    def create(self, validated_data):
        from core.services.weaving_machine import create_spec

        return create_spec(self.context["machine"], **validated_data)


class SpecUpdateSerializer(serializers.Serializer):
    needles_per_inch = optional_decimal("Gauge (n/inch)")
    width = optional_decimal("Machine width")

    def update(self, instance, validated_data):
        from core.services.weaving_machine import update_spec

        return update_spec(instance, **validated_data)
