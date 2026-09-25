from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError

from core.constant import GRID_SNAPSHOT_SCHEMA_VERSION, GRID_TILE_SIZE, RevisionTypeEnum
from core.exceptions import RevisionConflict
from core.models import DesignFile, DesignFileRevision, Part, PartStep, WorkflowStepDefinition
from core.permissions import require_design
from core.responses import revision_conflict_response, success_response
from core.serializers.design_serializers import (
    CompleteDesignFileRevisionSerializer,
    DesignFileRevisionDetailSerializer,
    DesignFileRevisionSaveSerializer,
    DesignFileTilesPatchSerializer,
    DesignFileTilesQuerySerializer,
    DesignWorkspaceSerializer,
    RestoreDesignFileRevisionSerializer,
    validate_design_file_type,
)
from core.services.design_grid.snapshot import read_tiles_from_snapshot
from core.services.design_workspace import get_or_create_workspace
from core.utils import get_instance, global_response_errors

from ..documents.design_documents import (
    design_file_autosave_document,
    design_file_complete_document,
    design_file_save_document,
    get_design_file_tiles_document,
    get_design_workspace_document,
    patch_design_file_tiles_document,
    restore_design_file_revision_document,
)


class DesignWorkspaceViewSet(viewsets.ViewSet):
    STEP_CODE = "START_DESIGNING"

    def _get_designing_part_step(self, part: Part) -> PartStep:
        step = WorkflowStepDefinition.objects.filter(code=self.STEP_CODE).first()
        if not step:
            raise NotFound("Workflow step not found!")
        try:
            return PartStep.objects.select_related("step").get(part=part, step=step)
        except PartStep.DoesNotExist:
            raise NotFound("Part step not found!")

    def _get_design_file(self, part_step: PartStep, file_type: str) -> DesignFile:
        validate_design_file_type(file_type)
        workspace = get_or_create_workspace(part_step, user=None)
        design_file = workspace.files.filter(file_type=file_type).first()
        if not design_file:
            raise NotFound("Design file not found!")
        return design_file

    @extend_schema(**get_design_workspace_document)
    @action(
        detail=True,
        methods=["get"],
        url_path=r"steps/START_DESIGNING/workspace",
    )
    def workspace(self, request, pk=None):
        part = get_instance(Part, pk)
        part_step = self._get_designing_part_step(part)
        workspace = get_or_create_workspace(part_step, user=request.user)
        workspace = (
            type(workspace)
            .objects.select_related(
                "part_step__part__source_document__work_item",
            )
            .prefetch_related("files__latest_revision", "files__official_revision")
            .get(pk=workspace.pk)
        )
        return success_response(
            DesignWorkspaceSerializer(workspace).data,
            "Design workspace retrieved successfully!",
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"steps/START_DESIGNING/files/(?P<file_type>[^/.]+)",
    )
    def file_detail(self, request, pk=None, file_type=None):
        part = get_instance(Part, pk)
        part_step = self._get_designing_part_step(part)
        design_file = self._get_design_file(part_step, file_type)
        design_file = (
            DesignFile.objects.select_related("latest_revision", "official_revision")
            .get(pk=design_file.pk)
        )
        revision = design_file.official_revision or design_file.latest_revision
        data = {
            "file_type": design_file.file_type,
            "official_revision": (
                DesignFileRevisionDetailSerializer(revision).data if revision else None
            ),
        }
        return success_response(data, "Design file retrieved successfully!")

    @action(
        detail=True,
        methods=["get"],
        url_path=r"steps/START_DESIGNING/files/(?P<file_type>[^/.]+)/revisions",
    )
    def file_revisions(self, request, pk=None, file_type=None):
        part = get_instance(Part, pk)
        part_step = self._get_designing_part_step(part)
        design_file = self._get_design_file(part_step, file_type)
        revisions = design_file.revisions.select_related(
            "snapshot_file", "preview_file", "created_by"
        ).order_by("-revision_no")
        return success_response(
            DesignFileRevisionDetailSerializer(revisions, many=True).data,
            "Design file revisions retrieved successfully!",
        )

    @extend_schema(**design_file_autosave_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"steps/START_DESIGNING/files/(?P<file_type>[^/.]+)/autosave",
    )
    def file_autosave(self, request, pk=None, file_type=None):
        return self._save_design_file(
            request,
            pk,
            file_type,
            RevisionTypeEnum.AUTOSAVE.value,
            "Design file autosaved successfully!",
        )

    @extend_schema(**design_file_save_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"steps/START_DESIGNING/files/(?P<file_type>[^/.]+)/save",
    )
    def file_save(self, request, pk=None, file_type=None):
        return self._save_design_file(
            request,
            pk,
            file_type,
            RevisionTypeEnum.MANUAL.value,
            "Design file saved successfully!",
        )

    @extend_schema(**design_file_complete_document)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"steps/START_DESIGNING/files/(?P<file_type>[^/.]+)/complete",
    )
    def file_complete(self, request, pk=None, file_type=None):
        require_design(request.user)
        part = get_instance(Part, pk)
        part_step = self._get_designing_part_step(part)
        design_file = self._get_design_file(part_step, file_type)
        revision = design_file.latest_revision
        if request.data:
            serializer = DesignFileRevisionSaveSerializer(
                data=request.data,
                context={"request": request},
            )
            if not serializer.is_valid():
                return global_response_errors(serializer.errors)
            try:
                revision = serializer.save_revision(
                    design_file=design_file,
                    revision_type=RevisionTypeEnum.MANUAL.value,
                )
            except RevisionConflict as exc:
                return revision_conflict_response(exc)
            except ValidationError as exc:
                return global_response_errors(exc.detail)
        if not revision:
            return global_response_errors({"revision": "No revision to complete!"})
        try:
            revision = CompleteDesignFileRevisionSerializer(
                context={"request": request}
            ).complete(revision=revision)
        except ValidationError as exc:
            return global_response_errors(exc.detail)
        return success_response(
            DesignFileRevisionDetailSerializer(revision).data,
            "Design file completed successfully!",
            status.HTTP_201_CREATED,
        )

    def _save_design_file(self, request, pk, file_type, revision_type, message):
        require_design(request.user)
        part = get_instance(Part, pk)
        part_step = self._get_designing_part_step(part)
        design_file = self._get_design_file(part_step, file_type)
        serializer = DesignFileRevisionSaveSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            try:
                revision = serializer.save_revision(
                    design_file=design_file,
                    revision_type=revision_type,
                )
            except RevisionConflict as exc:
                return revision_conflict_response(exc)
            except ValidationError as exc:
                return global_response_errors(exc.detail)
            return success_response(
                DesignFileRevisionDetailSerializer(revision).data,
                message,
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)


class DesignFileRevisionViewSet(viewsets.ViewSet):
    serializer_class = DesignFileRevisionDetailSerializer

    @extend_schema(methods=["GET"], **get_design_file_tiles_document)
    @extend_schema(methods=["PATCH"], **patch_design_file_tiles_document)
    @action(detail=True, methods=["get", "patch"], url_path="tiles")
    def tiles(self, request, pk=None):
        revision = get_instance(DesignFileRevision, pk)
        revision = DesignFileRevision.objects.select_related("snapshot_file").get(
            pk=revision.pk
        )
        if request.method == "PATCH":
            require_design(request.user)
            from core.services.design_files import is_grid_design_file

            if not is_grid_design_file(revision.design_file.file_type):
                return global_response_errors(
                    {"file_type": "Grid tiles API is only available for S1!"}
                )
            serializer = DesignFileTilesPatchSerializer(
                data=request.data,
                context={"request": request},
            )
            if serializer.is_valid():
                revision = serializer.apply(revision=revision)
                return success_response(
                    DesignFileRevisionDetailSerializer(revision).data,
                    "Tiles updated successfully!",
                )
            return global_response_errors(serializer.errors)

        query = DesignFileTilesQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return global_response_errors(query.errors)
        x0 = query.validated_data["x0"]
        y0 = query.validated_data["y0"]
        x1 = query.validated_data.get("x1") or revision.grid_width
        y1 = query.validated_data.get("y1") or revision.grid_height
        from core.services.design_grid.tile_codec import normalize_tile_update_bytes

        tiles = read_tiles_from_snapshot(
            snapshot_file=revision.snapshot_file,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
        )
        normalized_tiles = {}
        for key, hex_value in tiles.items():
            try:
                normalized_tiles[key] = normalize_tile_update_bytes(
                    bytes.fromhex(hex_value)
                ).hex()
            except (ValueError, TypeError):
                normalized_tiles[key] = hex_value
        return success_response(
            {
                "revision_id": str(revision.id),
                "schema_version": GRID_SNAPSHOT_SCHEMA_VERSION,
                "tile_size": GRID_TILE_SIZE,
                "grid_width": revision.grid_width,
                "grid_height": revision.grid_height,
                "viewport": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                "tiles": normalized_tiles,
            },
            "Tiles retrieved successfully!",
        )

    @extend_schema(**restore_design_file_revision_document)
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        require_design(request.user)
        revision = get_instance(DesignFileRevision, pk)
        serializer = RestoreDesignFileRevisionSerializer(context={"request": request})
        new_revision = serializer.restore(revision=revision)
        return success_response(
            DesignFileRevisionDetailSerializer(new_revision).data,
            "Design file revision restored successfully!",
            status.HTTP_201_CREATED,
        )
