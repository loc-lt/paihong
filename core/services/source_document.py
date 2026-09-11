from core.constant import (
    ALLOWED_SOURCE_EXTENSIONS,
    MAX_IMAGE_SIZE,
    SourceDocumentStatusEnum,
)
from core.models import SourceDocument
from core.services.file_storage import store_uploaded_file


def validate_source_upload(uploaded_file) -> None:
    from rest_framework import serializers

    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError("Source file must be smaller than 50 MB!")
    filename = uploaded_file.name or ""
    if "." not in filename:
        raise serializers.ValidationError("Source file must have a valid extension!")
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in ALLOWED_SOURCE_EXTENSIONS:
        allowed = ", ".join(ext.upper() for ext in ALLOWED_SOURCE_EXTENSIONS)
        raise serializers.ValidationError(f"Source file must be one of: {allowed}!")


def create_source_document(
    *,
    work_item,
    uploaded,
    user,
    sequence: int,
    status: int | None = None,
    metadata=None,
):
    validate_source_upload(uploaded)
    file_object = store_uploaded_file(uploaded, created_by=user)
    original_filename = uploaded.name
    extension = original_filename.rsplit(".", 1)[-1].lower()
    return SourceDocument.objects.create(
        work_item=work_item,
        file=file_object,
        sequence=sequence,
        original_filename=original_filename,
        document_type=extension,
        status=status or SourceDocumentStatusEnum.UPLOADED.value,
        metadata=metadata or {},
        uploaded_by=user,
        updated_by=user,
    )
