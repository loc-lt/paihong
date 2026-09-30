from __future__ import annotations

from django.db import transaction
from django.db.models import Max

from core.models import FileObject, Part, RevisionArtifact, SourceDocument
from core.services.design_workspace import delete_design_workspace_for_part
from core.services.file_storage import delete_file_object_if_unreferenced
from core.services.part_detection import create_parts_from_detection


@transaction.atomic
def create_manual_part(
    *,
    source_document: SourceDocument,
    preview_file: FileObject,
    name: str = "",
    user=None,
) -> Part:
    """Add a part by hand; it goes through the same step bootstrap as PDF import."""
    current = source_document.parts.aggregate(max_no=Max("sequence")).get("max_no")
    sequence = (current or 0) + 1
    [part] = create_parts_from_detection(
        source_document=source_document,
        parts_data=[
            {
                "sequence": sequence,
                "name": name or f"Part {sequence}",
                "preview_file": preview_file,
                "detected_metadata": {
                    "source": "manual",
                    "source_document_id": str(source_document.id),
                },
            }
        ],
        user=user,
    )
    return part


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
