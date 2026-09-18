from django.db import transaction
from django.db.models import Count, Exists, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from core.constant import StepStatusEnum, WorkItemStatusEnum
from core.models import Part, PartStep, SourceDocument, WorkItem
from core.services.part_detection import process_source_document_with_ai
from core.services.part_workflow import ensure_work_item_template, get_default_workflow_template
from core.services.source_document import create_source_document


def _work_item_parts_subquery():
    return (
        Part.objects.filter(source_document__work_item=OuterRef("pk"))
        .order_by()
        .values("source_document__work_item")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )


def _work_item_completed_parts_subquery():
    incomplete_steps = PartStep.objects.filter(part=OuterRef("pk")).exclude(
        status=StepStatusEnum.DONE.value
    )
    any_steps = PartStep.objects.filter(part=OuterRef("pk"))
    return (
        Part.objects.filter(source_document__work_item=OuterRef("pk"))
        .filter(Exists(any_steps))
        .exclude(Exists(incomplete_steps))
        .order_by()
        .values("source_document__work_item")
        .annotate(c=Count("id"))
        .values("c")[:1]
    )


def annotate_work_item_parts_progress(queryset):
    return queryset.annotate(
        parts_count=Coalesce(
            Subquery(_work_item_parts_subquery(), output_field=IntegerField()),
            0,
        ),
        completed_parts=Coalesce(
            Subquery(
                _work_item_completed_parts_subquery(), output_field=IntegerField()
            ),
            0,
        ),
    )


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

    work_item = annotate_work_item_parts_progress(
        WorkItem.objects.select_related(
            "created_by",
            "updated_by",
            "workflow_template",
        )
    ).get(pk=work_item.pk)

    return {
        "work_item": work_item,
        "source_documents": source_documents,
        "parts": parts,
    }
