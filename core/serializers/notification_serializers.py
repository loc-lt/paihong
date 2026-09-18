from rest_framework import serializers

from core.models import Notification
from core.serializers.user_serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "notify_type",
            "data",
            "is_read",
            "created",
            "modified",
        ]
        read_only_fields = fields
