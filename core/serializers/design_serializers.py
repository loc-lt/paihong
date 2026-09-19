import base64
import binascii

from rest_framework import serializers

from core.constant import DESIGN_FILE_SEQUENCE, RevisionTypeEnum
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
            "tile_manifest",
            "created_by",
            "created",
        ]
        read_only_fields = fields


class DesignFileSerializer(serializers.ModelSerializer):
    latest_revision = DesignFileRevisionSummarySerializer(read_only=True)
    official_revision = DesignFileRevisionSummarySerializer(read_only=True)
    lock_state = serializers.SerializerMethodField()

    class Meta:
        model = DesignFile
        fields = [
            "id",
            "file_type",
            "latest_revision",
            "official_revision",
            "lock_state",
            "created",
            "modified",
        ]
        read_only_fields = fields

    def get_lock_state(self, obj):
        from core.services.design_workspace import get_file_lock_state

        return get_file_lock_state(obj)


class DesignWorkspaceSerializer(serializers.ModelSerializer):
    files = DesignFileSerializer(many=True, read_only=True)

    class Meta:
        model = DesignWorkspace
        fields = [
            "id",
            "part_step",
            "settings",
            "files",
            "created",
            "modified",
        ]
        read_only_fields = fields


class DesignFileRevisionSaveSerializer(serializers.Serializer):
    layers = serializers.JSONField(required=False)
    tile_manifest = serializers.JSONField(required=False)
    base_revision_id = serializers.UUIDField(required=False, allow_null=True)

    def save_revision(self, *, design_file, revision_type, mark_official=False):
        from core.services.design_workspace import create_design_file_revision

        latest = design_file.latest_revision
        if self.validated_data.get("base_revision_id") and latest:
            if str(latest.id) != str(self.validated_data["base_revision_id"]):
                from core.exceptions import RevisionConflict

                raise RevisionConflict(
                    {"base_revision_id": "Revision conflict. Please reload and try again!"}
                )

        return create_design_file_revision(
            design_file=design_file,
            revision_type=revision_type,
            layers=self.validated_data.get("layers"),
            tile_manifest=self.validated_data.get("tile_manifest"),
            user=self.context["request"].user,
            mark_official=mark_official,
        )


class DesignFileTilesQuerySerializer(serializers.Serializer):
    x0 = serializers.IntegerField(min_value=0, default=0)
    y0 = serializers.IntegerField(min_value=0, default=0)
    x1 = serializers.IntegerField(min_value=1, required=False)
    y1 = serializers.IntegerField(min_value=1, required=False)


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

        from core.services.design_grid.snapshot import write_tiles_to_snapshot

        tile_updates = {
            item["key"]: base64.b64decode(item["data"])
            for item in self.validated_data["tiles"]
        }
        merged_file = write_tiles_to_snapshot(
            snapshot_file=revision.snapshot_file,
            tile_updates={key: value.hex() for key, value in tile_updates.items()},
            created_by=self.context["request"].user,
        )
        manifest = dict(revision.tile_manifest or {})
        manifest.update({key: value.hex() for key, value in tile_updates.items()})
        revision.snapshot_file = merged_file
        revision.tile_manifest = manifest
        revision.save(update_fields=["snapshot_file", "tile_manifest", "modified"])
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
