import os

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.constant import PartStatusEnum, SourceDocumentStatusEnum
from core.models import Part
from core.services.file_storage import read_file_object_bytes, store_bytes_content
from core.services.part_workflow import (
    bootstrap_completed_part_steps,
    ensure_work_item_template,
    initialize_part_steps,
)
from core.services.source_document_converter import FileToSvgConverter


def detect_parts_from_source_document(source_document, user=None) -> list[dict]:
    """
    Convert a source document (PDF/AI/DXF) into one Part per SVG page/component.
    """
    file_object = source_document.file
    file_bytes = read_file_object_bytes(file_object)
    filename = source_document.original_filename

    try:
        list_svg, _svg_full = FileToSvgConverter.process_file(file_bytes, filename)
    except ValueError as exc:
        raise ValidationError({"file": str(exc)}) from exc

    if not list_svg:
        raise ValidationError({"file": "No parts could be extracted from the source file!"})

    base_name = os.path.splitext(filename)[0] or "Part"
    extension = os.path.splitext(filename)[1].lower()
    multi_part = len(list_svg) > 1

    parts_data = []
    for index, svg_str in enumerate(list_svg, start=1):
        preview_file = store_bytes_content(
            svg_str.encode("utf-8"),
            filename=f"{base_name}_part_{index}.svg",
            created_by=user,
        )
        name = f"{base_name} - Part {index}" if multi_part else base_name
        parts_data.append(
            {
                "sequence": index,
                "name": name,
                "preview_file": preview_file,
                "source_page": index if extension in (".pdf", ".ai") else None,
                "detected_metadata": {
                    "source": "file_converter",
                    "source_document_id": str(source_document.id),
                    "page_index": index,
                    "total_pages": len(list_svg),
                    "original_filename": filename,
                },
            }
        )
    return parts_data


@transaction.atomic
def create_parts_from_detection(
    *,
    source_document,
    parts_data: list[dict],
    user=None,
    bootstrap_steps: bool = True,
) -> list[Part]:
    ensure_work_item_template(source_document.work_item)
    created_parts = []
    for index, part_data in enumerate(parts_data, start=1):
        sequence = part_data.get("sequence", index)
        preview_file = part_data.get("preview_file")

        part = Part.objects.create(
            source_document=source_document,
            sequence=sequence,
            name=part_data.get("name", ""),
            status=PartStatusEnum.NEW.value,
            source_page=part_data.get("source_page"),
            source_bbox=part_data.get("source_bbox") or {},
            preview_file=preview_file,
            detected_metadata=part_data.get("detected_metadata") or {},
            created_by=user,
            updated_by=user,
        )
        initialize_part_steps(part, user=user)
        if bootstrap_steps:
            bootstrap_completed_part_steps(part, user=user)
        created_parts.append(part)
    return created_parts


@transaction.atomic
def process_source_document_with_ai(
    *,
    source_document,
    user=None,
    bootstrap_steps: bool = True,
) -> list[Part]:
    try:
        parts_data = detect_parts_from_source_document(
            source_document,
            user=user,
        )
    except ValidationError:
        source_document.status = SourceDocumentStatusEnum.FAILED.value
        source_document.updated_by = user
        source_document.save(update_fields=["status", "updated_by", "modified"])
        raise

    source_document.status = SourceDocumentStatusEnum.PROCESSED.value
    source_document.updated_by = user
    source_document.save(update_fields=["status", "updated_by", "modified"])
    return create_parts_from_detection(
        source_document=source_document,
        parts_data=parts_data,
        user=user,
        bootstrap_steps=bootstrap_steps,
    )
