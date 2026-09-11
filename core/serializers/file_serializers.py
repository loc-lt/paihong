from rest_framework import serializers

from core.models import FileObject
from core.services.file_storage import get_file_url


class FileObjectSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = FileObject
        fields = [
            "id",
            "storage_backend",
            "storage_key",
            "extension",
            "mime_type",
            "size_bytes",
            "sha256",
            "metadata",
            "url",
            "created",
        ]
        read_only_fields = fields

    def get_url(self, obj):
        return get_file_url(obj.storage_key, obj.storage_backend)
