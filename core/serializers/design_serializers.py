import base64
import binascii

from rest_framework import serializers

from core.constant import RevisionTypeEnum
from core.services.design_files import DESIGN_FILE_SEQUENCE, build_design_file_display_name
from core.models import DesignFile, DesignFileRevision, DesignWorkspace
from core.serializers.file_serializers import FileObjectSerializer


class DesignFileRevisionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignFileRevision
        fields = [
            "id",
            "revision_no",
            "revision_type",
            "grid_width",
            "grid_height",
            "created_by",
            "created",
        ]
        read_only_fields = fields


class DesignFileRevisionDetailSerializer(serializers.ModelSerializer):
    snapshot_file = FileObjectSerializer(read_only=True)
    preview_file = FileObjectSerializer(read_only=True)

    class Meta:
        model = DesignFileRevision
        fields = [
            "id",
            "design_file",
            "revision_no",
            "revision_type",
            "parent_revision",
            "layers",
            "grid_width",
            "grid_height",
            "snapshot_file",
            "preview_file",
            "created_by",
            "created",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        from core.services.design_grid.tile_codec import normalize_layers

        data = super().to_representation(instance)
        try:
            data["layers"] = normalize_layers(instance.layers or [])
        except ValueError:
            data["layers"] = instance.layers or []
        return data


class DesignFileSerializer(serializers.ModelSerializer):
    latest_revision = DesignFileRevisionSummarySerializer(read_only=True)
    official_revision = DesignFileRevisionSummarySerializer(read_only=True)
    display_name = serializers.SerializerMethodField()
    has_grid = serializers.SerializerMethodField()

    class Meta:
        model = DesignFile
        fields = [
            "id",
            "file_type",
            "display_name",
            "has_grid",
            "latest_revision",
            "official_revision",
            "created",
            "modified",
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        product_code = self.context.get("product_code")
        if not product_code:
            part_step = getattr(obj.workspace, "part_step", None)
            if part_step:
                product_code = part_step.part.work_item.item_code
        return build_design_file_display_name(product_code or "", obj.file_type)

    def get_has_grid(self, obj):
        from core.services.design_files import is_grid_design_file

        return is_grid_design_file(obj.file_type)


class DesignWorkspaceSerializer(serializers.ModelSerializer):
    files = DesignFileSerializer(many=True, read_only=True)
    product_code = serializers.SerializerMethodField()

    class Meta:
        model = DesignWorkspace
        fields = [
            "id",
            "part_step",
            "product_code",
            "settings",
            "files",
            "created",
            "modified",
        ]
        read_only_fields = fields

    def get_product_code(self, obj):
        return obj.part_step.part.work_item.item_code

    def to_representation(self, instance):
        product_code = instance.part_step.part.work_item.item_code
        self.fields["files"].context["product_code"] = product_code
        return super().to_representation(instance)


class DesignLayerSerializer(serializers.Serializer):
    color_code = serializers.CharField(
        help_text="Layer key in #RRGGBB format. Must match paints in tile cells.",
    )
    name = serializers.CharField(required=False, default="", allow_blank=True)
    z_order = serializers.IntegerField(required=False, min_value=1)
    is_hidden = serializers.BooleanField(required=False, default=False)
    is_lock = serializers.BooleanField(required=False, default=False)


class DesignFileRevisionSaveSerializer(serializers.Serializer):
    layers = DesignLayerSerializer(
        many=True,
        required=False,
        help_text=(
            "Layer panel metadata (name, z-order, hidden, lock). "
            "Does not mutate tile blobs — send PATCH tiles for cell paint data."
        ),
    )
    base_revision_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Latest revision id for optimistic concurrency (409 if stale).",
    )

    def validate_layers(self, value):
        if value is None:
            return None
        from core.services.design_grid.tile_codec import normalize_layers

        try:
            return normalize_layers(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def save_revision(self, *, design_file, revision_type, mark_official=False):
        from core.exceptions import RevisionConflict
        from core.models import DesignFileRevision
        from core.services.design_files import is_grid_design_file
        from core.services.design_grid.preview import refresh_design_file_revision_preview
        from core.services.design_workspace import create_design_file_revision

        user = self.context["request"].user
        layers = self.validated_data.get("layers")
        base_revision_id = self.validated_data.get("base_revision_id")
        latest = design_file.latest_revision

        if layers is not None and not is_grid_design_file(design_file.file_type):
            raise serializers.ValidationError(
                {
                    "file_type": (
                        f"Layer panel save is only supported for S1, "
                        f"not {design_file.file_type}!"
                    )
                }
            )

        if base_revision_id:
            base_revision = (
                DesignFileRevision.objects.filter(pk=base_revision_id)
                .select_related("design_file")
                .first()
            )
            if not base_revision:
                raise serializers.ValidationError(
                    {"base_revision_id": "Revision not found!"}
                )
            if base_revision.design_file_id != design_file.id:
                raise serializers.ValidationError(
                    {
                        "base_revision_id": (
                            f"Revision belongs to file "
                            f"{base_revision.design_file.file_type}, "
                            f"not {design_file.file_type}! "
                            f"Use /files/{base_revision.design_file.file_type}/save."
                        )
                    }
                )
            if latest and str(latest.id) != str(base_revision_id):
                raise RevisionConflict(
                    {"base_revision_id": "Revision conflict. Please reload and try again!"}
                )

        if latest is None:
            raise serializers.ValidationError(
                {
                    "revision": (
                        f"No revision for file {design_file.file_type} yet. "
                        "Grid layers must be saved on S1 after BUILD_GRID."
                    )
                }
            )

        revision = create_design_file_revision(
            design_file=design_file,
            revision_type=revision_type,
            layers=layers,
            user=user,
            mark_official=mark_official,
        )

        if is_grid_design_file(design_file.file_type):
            refresh_design_file_revision_preview(revision=revision, user=user)

        return revision


class DesignFileTilesQuerySerializer(serializers.Serializer):
    x0 = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Left column of the viewport in grid pixel space (inclusive).",
    )
    y0 = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Top row of the viewport in grid pixel space (inclusive).",
    )
    x1 = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text=(
            "Right column of the viewport (exclusive). "
            "Defaults to revision grid_width when omitted."
        ),
    )
    y1 = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text=(
            "Bottom row of the viewport (exclusive). "
            "Defaults to revision grid_height when omitted."
        ),
    )


class DesignFileTilesViewportSerializer(serializers.Serializer):
    x0 = serializers.IntegerField()
    y0 = serializers.IntegerField()
    x1 = serializers.IntegerField()
    y1 = serializers.IntegerField()


class DesignFileTilesResponseSerializer(serializers.Serializer):
    revision_id = serializers.UUIDField()
    schema_version = serializers.IntegerField()
    tile_size = serializers.IntegerField()
    grid_width = serializers.IntegerField()
    grid_height = serializers.IntegerField()
    viewport = DesignFileTilesViewportSerializer()
    tiles = serializers.DictField(
        child=serializers.CharField(),
        help_text='Tile payload keyed by "tx_ty", values are hex-encoded tile JSON.',
    )


class TileUpdateSerializer(serializers.Serializer):
    key = serializers.RegexField(regex=r"^\d+_\d+$")
    data = serializers.CharField()

    def validate_data(self, value):
        try:
            base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise serializers.ValidationError("Tile data must be valid base64!") from exc
        return value


class DesignFileTilesPatchSerializer(serializers.Serializer):
    tiles = TileUpdateSerializer(many=True, allow_empty=False)

    def apply(self, *, revision):
        import base64

        from core.services.design_grid.preview import refresh_design_file_revision_preview
        from core.services.design_grid.snapshot import write_tiles_to_snapshot
        from core.services.design_grid.tile_codec import normalize_tile_update_bytes

        user = self.context["request"].user
        tile_updates = {}
        for item in self.validated_data["tiles"]:
            try:
                raw = normalize_tile_update_bytes(base64.b64decode(item["data"]))
            except ValueError as exc:
                raise serializers.ValidationError(
                    {"tiles": f"Tile {item['key']}: {exc}"}
                ) from exc
            tile_updates[item["key"]] = raw
        merged_file = write_tiles_to_snapshot(
            snapshot_file=revision.snapshot_file,
            tile_updates={key: value.hex() for key, value in tile_updates.items()},
            created_by=user,
        )
        manifest = dict(revision.tile_manifest or {})
        manifest.update({key: value.hex() for key, value in tile_updates.items()})
        revision.snapshot_file = merged_file
        revision.tile_manifest = manifest
        revision.save(update_fields=["snapshot_file", "tile_manifest", "modified"])
        refresh_design_file_revision_preview(revision=revision, user=user)
        return revision


class CompleteDesignFileRevisionSerializer(serializers.Serializer):
    def complete(self, *, revision):
        from core.services.design_workspace import complete_design_file_revision

        return complete_design_file_revision(revision=revision, user=self.context["request"].user)


class RestoreDesignFileRevisionSerializer(serializers.Serializer):
    def restore(self, *, revision):
        from core.services.design_workspace import restore_design_file_revision

        return restore_design_file_revision(revision=revision, user=self.context["request"].user)


def validate_design_file_type(value: str) -> str:
    if value not in DESIGN_FILE_SEQUENCE:
        allowed = ", ".join(DESIGN_FILE_SEQUENCE)
        raise serializers.ValidationError(f"File type must be one of: {allowed}!")
    return value
