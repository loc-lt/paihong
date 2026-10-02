from __future__ import annotations

from django.db import transaction
from django.db.models import Max

from core.models import FileObject, Part, RevisionArtifact, SourceDocument
from core.services.design_workspace import delete_design_workspace_for_part
from core.services.file_storage import delete_file_object_if_unreferenced
from core.services.part_detection import create_parts_from_detection


@transaction.atomic
def create_manual_parts(
    *,
    source_document: SourceDocument,
    items: list[dict],
    user=None,
) -> list[Part]:
    """Add parts by hand; each one goes through the same step bootstrap as PDF import."""
    current = source_document.parts.aggregate(max_no=Max("sequence")).get("max_no") or 0
    named = source_document.parts.count()
    parts_data = []
    for offset, item in enumerate(items, start=1):
        sequence = current + offset
        parts_data.append(
            {
                "sequence": sequence,
                "name": f"New part {named + offset}",
                "preview_file": item["preview_file"],
                "detected_metadata": {
                    "source": "manual",
                    "source_document_id": str(source_document.id),
                },
            }
        )
    return create_parts_from_detection(
        source_document=source_document,
        parts_data=parts_data,
        user=user,
    )


@transaction.atomic
def delete_parts(parts: list[Part], user=None) -> int:
    for part in parts:
        delete_part(part, user=user)
    return len(parts)


@transaction.atomic
def delete_part(part: Part, user=None) -> None:
    file_object_ids = set(
        RevisionArtifact.objects.filter(revision__part_step__part=part).values_list(
            "file_id", flat=True
        )
    )
    if part.preview_file_id:
        file_object_ids.add(part.preview_file_id)

    delete_design_workspace_for_part(part, user=user)
    part.delete()

    for file_obj in FileObject.objects.filter(pk__in=file_object_ids):
        delete_file_object_if_unreferenced(file_obj)
