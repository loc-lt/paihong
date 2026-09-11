from rest_framework import serializers


class BoundedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(
        self,
        *,
        min_value,
        max_value,
        pk_error_messages,
        **kwargs,
    ):
        self.pk_validator = serializers.IntegerField(
            min_value=min_value,
            max_value=max_value,
            error_messages=pk_error_messages,
        )
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        validated_pk = self.pk_validator.run_validation(data)
        return super().to_internal_value(validated_pk)


class BoundedUUIDRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(
        self,
        *,
        uuid_error_messages=None,
        **kwargs,
    ):
        self.uuid_field = serializers.UUIDField(
            error_messages=uuid_error_messages
            or {
                "invalid": "Invalid ID format!",
            }
        )
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        validated_uuid = self.uuid_field.run_validation(data)
        return super().to_internal_value(validated_uuid)
