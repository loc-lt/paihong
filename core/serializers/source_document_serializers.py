from rest_framework import serializers

from core.models import SourceDocument
from core.serializers.file_serializers import FileObjectSerializer


class SourceDocumentSerializer(serializers.ModelSerializer):
    file = FileObjectSerializer(read_only=True)

    class Meta:
        model = SourceDocument
        fields = [
            "id",
            "work_item",
            "file",
            "sequence",
            "original_filename",
            "document_type",
            "status",
            "metadata",
            "uploaded_by",
            "updated_by",
            "created",
            "modified",
        ]
        read_only_fields = fields
