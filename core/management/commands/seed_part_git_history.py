from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.constant import (
    DEFAULT_OUTPUT_ARTIFACT_ROLE,
    WORKFLOW_STEP_SEED,
    RevisionTypeEnum,
    SourceDocumentStatusEnum,
)
from core.models import (
    FileObject,
    Part,
    PartBranch,
    PartStep,
    RevisionArtifact,
    SourceDocument,
    StepRevision,
    WorkItem,
)
from core.services.file_storage import (
    delete_file_object_if_unreferenced,
    store_unique_bytes,
)
from core.services.part_branch import attach_official_revision
from core.services.part_history import upstream_official_revision
from core.services.part_workflow import (
    get_default_workflow_template,
    initialize_part_steps,
)
from core.services.step_settings import wrap_settings

DEMO_ITEM_CODE = "GIT_DEMO"
STEP_CODES = [code for _sequence, code, _name in WORKFLOW_STEP_SEED]
# Each pass completes steps[start:end] inclusive, same rules as a real complete:
# parent = previous revision of that step, based_on = current official of the
# nearest earlier step. Later steps go back to not started; their revisions stay.
PASSES = (
    (0, 9, "First complete"),
    (5, 9, "Recheck colors"),
    (4, 9, "Move anchors"),
    (2, 9, "Fix rotation"),
    (1, 9, "Pick another upper"),
    (7, 9, "Adjust specs"),
    (8, 9, "Resize grid"),
    (3, 7, "Strip leftover lines"),
    (5, 8, "Color tweak and rebuild grid"),
)
# Minimal 1x1 PNG so SourceDocument.file is a real stored object.
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf"
    b"\xc0\x00\x00\x00\x03\x00\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _demo_settings(step_code: str, revision_no: int) -> dict:
    """Settings differ by revision so each branch node is visible in the demo."""
    n = revision_no
    data = {
        "RECEIVE_FILES": {},
        "PICK_UPPER": {
            "selected_candidate_index": n - 1,
            "rotation": n * 15,
            "candidates": [],
        },
        "ROTATE_STRIP_TEXT": {"rotation": n * 15},
        "REMOVE_AUX_LINES": {"removed_line_count": n},
        "FIX_LINES_BY_ANCHOR": {
            "anchors": [{"x": n * 10, "y": n * 5}],
            "snap_distance": float(n),
            "tolerance": 1,
        },
        "CHECK_COLORS": {
            "frame_expansion_mm": float(n),
            "corner_type": "sharp",
            "corner_limit": 4,
        },
        "CANVAS_FRAME_MEASURE": {
            "canvas": {"width_mm": 200 + n, "height_mm": 100 + n},
            "origin": {"x": 0, "y": 0},
            "scale": 1,
        },
        "ENTER_SPECS": {
            "needle_density": 14,
            "cos_number": n,
            "course_per_pixel": 2,
        },
        "BUILD_GRID": {"grid": {"width": 40 + n, "height": 20 + n}},
        "START_DESIGNING": {"active_file_type": "S1", "progress": {}},
    }
    return wrap_settings(data.get(step_code, {}), source="manual")

class Command(BaseCommand):
    help = (
        "Seed work item GIT_DEMO with workflow branches. "
        "Re-completing a step forks a branch. Completing the next step extends it. "
        "Idempotent."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        template = get_default_workflow_template()
        if not template:
            raise CommandError("No workflow template. Run seed_workflow_steps first!")

        existing = WorkItem.objects.filter(item_code=DEMO_ITEM_CODE).first()
        if existing:
            file_ids = list(existing.source_documents.values_list("file_id", flat=True))
            # head_revision is PROTECT, so branches must go before the work item.
            PartBranch.objects.filter(
                part__source_document__work_item=existing
            ).delete()
            existing.delete()
            for file_id in file_ids:
                file_object = FileObject.objects.filter(pk=file_id).first()
                if file_object:
                    delete_file_object_if_unreferenced(file_object)

        work_item = WorkItem.objects.create(
            item_code=DEMO_ITEM_CODE,
            name="Git history demo",
            workflow_template=template,
        )
        stored = store_unique_bytes(_PNG, filename="git_demo.png")
        source = SourceDocument.objects.create(
            work_item=work_item,
            file=stored,
            sequence=1,
            original_filename="git_demo.png",
            document_type="png",
            status=SourceDocumentStatusEnum.UPLOADED.value,
        )
        part = Part.objects.create(
            source_document=source,
            sequence=1,
            name="Git demo part",
        )
        initialize_part_steps(part)
        lanes = {
            code: PartStep.objects.select_related("step").get(part=part, step__code=code)
            for code in STEP_CODES
        }
        missing = [code for code in STEP_CODES if code not in lanes]
        if missing:
            raise CommandError(f"Part is missing steps: {', '.join(missing)}!")

        next_no = {code: 1 for code in STEP_CODES}
        created_at = timezone.now() - timedelta(days=3)
        total = 0

        for start, end, note in PASSES:
            for step_index in range(start, end + 1):
                code = STEP_CODES[step_index]
                part_step = PartStep.objects.select_related(
                    "step", "latest_revision"
                ).get(pk=lanes[code].pk)
                revision = StepRevision.objects.create(
                    part_step=part_step,
                    revision_no=next_no[code],
                    revision_type=RevisionTypeEnum.OFFICIAL.value,
                    parent_revision=part_step.latest_revision,
                    based_on_revision=upstream_official_revision(
                        part, part_step.step.sequence
                    ),
                    settings=_demo_settings(code, next_no[code]),
                    note=note,
                )
                stamped = created_at + timedelta(minutes=total * 30)
                StepRevision.objects.filter(pk=revision.pk).update(created=stamped)
                RevisionArtifact.objects.create(
                    revision=revision,
                    file=stored,
                    filename="git_demo.png",
                    role=DEFAULT_OUTPUT_ARTIFACT_ROLE,
                    sequence=0,
                    metadata={},
                )
                next_no[code] += 1
                total += 1
                attach_official_revision(part, revision)

        part.refresh_from_db()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {DEMO_ITEM_CODE} with {total} step revisions "
                f"and {part.branches.count()} branches. "
                f"current_branch_id={part.current_branch_id} "
                f"part_id={part.id} "
                f"GET /api/v1/parts/{part.id}/history"
            )
        )
