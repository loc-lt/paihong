from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from core.constant import RevisionTypeEnum, StepStatusEnum
from core.exceptions import RevisionConflict
from core.filters import StepRevisionFilter
from core.models import Part, PartStep, StepRevision, WorkflowStepDefinition
from core.paginators import CustomPaginator
from core.permissions import require_design
from core.responses import revision_conflict_response, success_response
from core.serializers.revision_serializers import (
    PartStepDetailSerializer,
    PartStepSerializer,
    PartStepsListSerializer,
    RestoreRevisionSerializer,
    SaveStepRevisionSerializer,
    StepRevisionDetailSerializer,
    PartHistorySerializer,
)
from core.services.part_workflow import sync_part_steps
from core.utils import get_instance, global_response_errors

from ..documents.revision_documents import (
    autosave_revision_document,
    checkout_part_branch_document,
    get_part_history_document,
    get_part_step_document,
    get_part_steps_document,
    get_revision_document,
    get_revisions_document,
    manual_save_revision_document,
    official_save_revision_document,
    restore_revision_document,
    sync_part_steps_document,
)


class PartWorkflowViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(**get_part_history_document)
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        from core.services.part_branch import list_part_branches

        part = get_instance(Part, pk)
        return success_response(
            PartHistorySerializer(list_part_branches(part)).data,
            "Part history retrieved successfully.",
        )

    @extend_schema(**checkout_part_branch_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"branches/(?P<branch_id>[^/.]+)/checkout",
    )
    def checkout_branch(self, request, pk=None, branch_id=None):
        from core.models import PartBranch
        from core.services.part_branch import checkout_branch as checkout_part_branch
        from core.services.part_branch import list_part_branches

        require_design(request.user)
        part = get_instance(Part, pk)
        branch = PartBranch.objects.filter(pk=branch_id, part=part).first()
        if branch is None:
            raise NotFound("Branch not found!")
        checkout_part_branch(part, branch, user=request.user)
        part.refresh_from_db()
        return success_response(
            PartHistorySerializer(list_part_branches(part)).data,
            "Branch checked out successfully!",
        )

    @extend_schema(**get_part_steps_document)
    @action(detail=True, methods=["get"], url_path="steps")
    def steps(self, request, pk=None):
        part = get_instance(Part, pk)
        queryset = (
            part.steps.select_related(
                "step",
                "latest_revision",
                "official_revision",
            )
            .prefetch_related(
                "latest_revision__artifacts__file",
                "official_revision__artifacts__file",
            )
            .order_by("step__sequence")
        )
        steps = list(queryset)
        serializer = PartStepsListSerializer(
            {
                "current_branch_id": part.current_branch_id,
                "steps": steps,
                "total_steps": len(steps),
                "completed_steps": sum(
                    1 for step in steps if step.status == StepStatusEnum.DONE.value
                ),
            }
        )
        return success_response(
            serializer.data,
            "Part steps retrieved successfully!",
        )

    @extend_schema(**sync_part_steps_document)
    @action(detail=True, methods=["post"], url_path="sync-steps")
    def sync_steps(self, request, pk=None):
        require_design(request.user)
        part = get_instance(Part, pk)
        synced = sync_part_steps(part, user=request.user)
        return success_response(
            PartStepSerializer(synced, many=True).data,
            "Part steps synced successfully!",
        )

    @extend_schema(**get_part_step_document)
    @action(detail=True, methods=["get"], url_path=r"steps/(?P<step_code>[^/.]+)")
    def step_detail(self, request, pk=None, step_code=None):
        part = get_instance(Part, pk)
        part_step = self._get_part_step(part, step_code)
        part_step = (
            PartStep.objects.select_related(
                "step",
                "latest_revision",
                "official_revision",
            )
            .prefetch_related(
                "latest_revision__artifacts__file",
                "official_revision__artifacts__file",
            )
            .get(pk=part_step.pk)
        )
        return success_response(
            PartStepDetailSerializer(part_step).data,
            "Part step retrieved successfully!",
        )

    @extend_schema(**get_revisions_document)
    @action(detail=True, methods=["get"], url_path=r"steps/(?P<step_code>[^/.]+)/revisions")
    def revisions(self, request, pk=None, step_code=None):
        part = get_instance(Part, pk)
        part_step = self._get_part_step(part, step_code)
        queryset = StepRevisionFilter(
            request.query_params,
            queryset=part_step.revisions.select_related("created_by").order_by(
                "-revision_no"
            ),
        ).qs
        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request)
        serializer = StepRevisionDetailSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(**autosave_revision_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"steps/(?P<step_code>[^/.]+)/autosave",
    )
    def autosave(self, request, pk=None, step_code=None):
        return self._save_revision(
            request,
            pk,
            step_code,
            RevisionTypeEnum.AUTOSAVE.value,
            "Autosave created successfully!",
        )

    @extend_schema(**manual_save_revision_document)
    @action(detail=True, methods=["post"], url_path=r"steps/(?P<step_code>[^/.]+)/save")
    def save_step(self, request, pk=None, step_code=None):
        return self._save_revision(
            request,
            pk,
            step_code,
            RevisionTypeEnum.MANUAL.value,
            "Revision saved successfully!",
        )

    @extend_schema(**official_save_revision_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"steps/(?P<step_code>[^/.]+)/complete",
    )
    def complete_step(self, request, pk=None, step_code=None):
        return self._save_revision(
            request,
            pk,
            step_code,
            RevisionTypeEnum.OFFICIAL.value,
            "Step completed successfully!",
            mark_step_done=True,
        )

    def _save_revision(
        self,
        request,
        pk,
        step_code,
        revision_type,
        message,
        mark_step_done=False,
    ):
        require_design(request.user)
        part = get_instance(Part, pk)
        part_step = self._get_part_step(part, step_code)
        serializer = SaveStepRevisionSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            try:
                result = serializer.create_revision(
                    part_step=part_step,
                    revision_type=revision_type,
                    mark_step_done=mark_step_done,
                )
            except RevisionConflict as exc:
                return revision_conflict_response(exc)
            except ValidationError as exc:
                return global_response_errors(exc.detail)

            revision = (
                StepRevision.objects.prefetch_related("artifacts__file")
                .get(pk=result.revision.pk)
            )
            part.refresh_from_db(fields=["current_branch"])
            response_data = StepRevisionDetailSerializer(revision).data
            if mark_step_done:
                next_settings = result.next_step_settings
                if next_settings:
                    from core.services.step_settings import unwrap_settings

                    settings_payload, settings_meta = unwrap_settings(
                        next_settings.get("settings")
                    )
                    next_payload = {
                        "step_code": next_settings.get("step_code"),
                        "settings": settings_payload,
                        "meta": settings_meta,
                    }
                else:
                    next_payload = None
                response_data = {
                    "branch_id": part.current_branch_id,
                    "revision": response_data,
                    "next_step_settings": next_payload,
                }
            return success_response(
                response_data,
                message,
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    def _get_part_step(self, part, step_code):
        step = WorkflowStepDefinition.objects.filter(code=step_code).first()
        if not step:
            raise NotFound("Workflow step not found!")
        try:
            return PartStep.objects.select_related(
                "step",
                "latest_revision",
                "official_revision",
            ).get(part=part, step=step)
        except PartStep.DoesNotExist:
            raise NotFound("Part step not found!")


class RevisionViewSet(viewsets.ViewSet):
    @extend_schema(**get_revision_document)
    def retrieve(self, request, pk=None):
        revision = get_instance(StepRevision, pk)
        revision = StepRevision.objects.prefetch_related("artifacts__file").get(
            pk=revision.pk
        )
        return success_response(
            StepRevisionDetailSerializer(revision).data,
            "Revision retrieved successfully!",
        )

    @extend_schema(**restore_revision_document)
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        require_design(request.user)
        revision = get_instance(StepRevision, pk)
        revision = StepRevision.objects.prefetch_related("artifacts__file").get(
            pk=revision.pk
        )
        serializer = RestoreRevisionSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            try:
                new_revision = serializer.restore(revision=revision)
            except RevisionConflict as exc:
                return revision_conflict_response(exc)
            except ValidationError as exc:
                return global_response_errors(exc.detail)
            return success_response(
                StepRevisionDetailSerializer(new_revision).data,
                "Revision restored successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)
