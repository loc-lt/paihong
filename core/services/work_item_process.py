from django.db import transaction

from core.constant import WorkItemStatusEnum
from core.models import Part, SourceDocument, WorkItem
from core.services.part_detection import process_source_document_with_ai
from core.services.part_workflow import ensure_work_item_template, get_default_workflow_template
from core.services.source_document import create_source_document


@transaction.atomic
def process_work_item(
    *,
    user,
    item_code: str,
    name: str = "",
    status: int | None = None,
    workflow_template=None,
    files: list,
) -> dict:
    if workflow_template is None:
        workflow_template = get_default_workflow_template()

    work_item = WorkItem.objects.create(
        item_code=item_code,
        name=name,
        status=status or WorkItemStatusEnum.NEW.value,
        workflow_template=workflow_template,
        created_by=user,
        updated_by=user,
    )
    ensure_work_item_template(work_item)

    source_documents: list[SourceDocument] = []
    parts: list[Part] = []

    for sequence, uploaded in enumerate(files, start=1):
        source_document = create_source_document(
            work_item=work_item,
            uploaded=uploaded,
            user=user,
            sequence=sequence,
        )
        source_documents.append(source_document)
        detected_parts = process_source_document_with_ai(
            source_document=source_document,
            user=user,
        )
        parts.extend(detected_parts)

    return {
        "work_item": work_item,
        "source_documents": source_documents,
        "parts": parts,
    }
