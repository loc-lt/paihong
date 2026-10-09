import os

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.constant import PartStatusEnum, SourceDocumentStatusEnum
from core.models import Part
from core.services.ai_design import AiOutputFileError, fetch_ai_json, store_ai_output_file
from core.services.file_storage import get_file_url, read_file_object_bytes, store_bytes_content
from core.services.part_workflow import (
    bootstrap_completed_part_steps,
    ensure_work_item_template,
    initialize_part_steps,
)
from core.services.pick_upper_candidates import build_pick_upper_candidates
from core.services.source_document_converter import FileToSvgConverter


def store_svg_files_from_split_regions(source_document, user=None) -> list:
    """Copy AI split_regions list_svg into object storage. Does not create parts."""
    file_object = source_document.file
    url_path = get_file_url(file_object.storage_key, file_object.storage_backend)
    if not url_path or not str(url_path).startswith(("http://", "https://")):
        raise ValidationError(
            {"file": "BE_DOMAIN is empty. Cannot send the source file URL to AI!"}
        )

    body = fetch_ai_json(
        "/api/v1/split_regions",
        {
            "url_path": url_path,
            "product_code": source_document.work_item.item_code,
        },
    )
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    list_svg = data.get("list_svg") or []
    if not isinstance(list_svg, list) or not list_svg:
        raise ValidationError({"file": "AI split_regions returned no SVG files!"})

    stored = []
    for path in list_svg:
        try:
            stored.append(store_ai_output_file(str(path), created_by=user))
        except AiOutputFileError as exc:
            raise ValidationError({"file": str(exc)}) from exc
    return stored


def detect_parts_from_source_document(source_document, user=None) -> list[dict]:
    """
    Convert a source document (PDF/AI/DXF) into one Part per SVG region.
    """
    file_object = source_document.file
    file_bytes = read_file_object_bytes(file_object)
    filename = source_document.original_filename

    try:
        list_svg, list_texts, _svg_full = FileToSvgConverter.process_file(
            file_bytes, filename
        )
    except ValueError as exc:
        raise ValidationError({"file": str(exc)}) from exc

    if not list_svg:
        raise ValidationError(
            {"file": "No parts could be extracted from the source file!"}
        )

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
        texts = list_texts[index - 1] if index - 1 < len(list_texts) else []
        detected_metadata = {
            "source": "file_converter",
            "source_document_id": str(source_document.id),
            "page_index": index,
            "total_pages": len(list_svg),
            "original_filename": filename,
            "texts": texts,
        }
        parts_data.append(
            {
                "sequence": index,
                "name": name,
                "preview_file": preview_file,
                "source_page": index if extension in (".pdf", ".ai") else None,
                "detected_metadata": detected_metadata,
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

        detected_metadata = dict(part_data.get("detected_metadata") or {})
        part = Part.objects.create(
            source_document=source_document,
            sequence=sequence,
            name=part_data.get("name", ""),
            status=PartStatusEnum.NEW.value,
            source_page=part_data.get("source_page"),
            source_bbox=part_data.get("source_bbox") or {},
            preview_file=preview_file,
            detected_metadata=detected_metadata,
            created_by=user,
            updated_by=user,
        )
        candidates = build_pick_upper_candidates(part=part)
        if candidates:
            detected_metadata["pick_upper_candidates"] = candidates
            part.detected_metadata = detected_metadata
            part.save(update_fields=["detected_metadata", "modified"])
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
        svg_files = store_svg_files_from_split_regions(source_document, user=user)
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
    source_document.svg_files.set(svg_files)
    return create_parts_from_detection(
        source_document=source_document,
        parts_data=parts_data,
        user=user,
        bootstrap_steps=bootstrap_steps,
    )
