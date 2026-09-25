import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django_extensions.db.models import TimeStampedModel
from django_softdelete.models import SoftDeleteModel

from core.constant import (
    PartStatusEnum,
    RevisionTypeEnum,
    SourceDocumentStatusEnum,
    StepStatusEnum,
    StorageBackendEnum,
    UserRoleEnum,
    UserStatusEnum,
    WorkItemStatusEnum,
)
from core.managers import DeletedUserManager, GlobalUserManager, SoftDeleteUserManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    username = models.CharField(max_length=150, unique=True, null=False, blank=False)
    first_name = models.CharField(
        max_length=150, null=False, blank=True, default=""
    )
    last_name = models.CharField(max_length=150, null=False, blank=True, default="")
    role = models.IntegerField(
        default=UserRoleEnum.CUSTOMER.value,
        null=False,
        blank=False,
        db_index=True,
    )
    status = models.IntegerField(
        default=UserStatusEnum.ACTIVE.value,
        null=False,
        blank=False,
        db_index=True,
    )
    avatar = models.ForeignKey(
        "FileObject",
        null=True,
        blank=True,
        related_name="user_avatars",
        on_delete=models.SET_NULL,
    )
    is_staff = models.BooleanField(null=False, default=False)
    token_version = models.UUIDField(
        default=uuid.uuid4, null=False, blank=False
    )

    objects = SoftDeleteUserManager()
    global_objects = GlobalUserManager()
    deleted_objects = DeletedUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def is_active(self):
        return self.status == UserStatusEnum.ACTIVE.value and not self.is_deleted

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def set_new_token_version(self):
        self.token_version = uuid.uuid4()
        self.save(update_fields=["token_version", "modified"])

    def get_new_token_version(self) -> str:
        return str(self.token_version)

    def is_token_version_valid(self, token_version: str) -> bool:
        return bool(self.get_new_token_version() == token_version)


class FileObject(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    storage_backend = models.IntegerField(
        default=StorageBackendEnum.LOCAL.value,
        null=False,
        blank=False,
    )
    storage_key = models.CharField(
        max_length=1000, unique=True, null=False, blank=False
    )
    extension = models.CharField(max_length=30, null=False, blank=True, default="")
    mime_type = models.CharField(max_length=150, null=False, blank=True, default="")
    size_bytes = models.BigIntegerField(null=False, blank=False)
    sha256 = models.CharField(max_length=64, null=False, blank=False, db_index=True)
    metadata = models.JSONField(default=dict, null=False, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_file_objects",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "file_object"
        indexes = [
            models.Index(
                fields=["sha256", "size_bytes"],
                name="idx_file_sha_size",
            ),
        ]

    def __str__(self):
        return self.storage_key


class WorkItem(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    item_code = models.CharField(max_length=255, unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=True, default="")
    status = models.IntegerField(
        default=WorkItemStatusEnum.NEW.value,
        null=False,
        blank=False,
        db_index=True,
    )
    workflow_template = models.ForeignKey(
        "WorkflowTemplate",
        null=True,
        blank=True,
        related_name="work_items",
        on_delete=models.PROTECT,
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_work_items",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_work_items",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "work_item"
        indexes = [
            models.Index(
                fields=["status", "-created"],
                name="idx_workitem_status_created",
            ),
        ]

    def __str__(self):
        return self.item_code


class SourceDocument(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    work_item = models.ForeignKey(
        WorkItem,
        related_name="source_documents",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    file = models.ForeignKey(
        FileObject,
        related_name="source_documents",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    svg_file = models.ForeignKey(
        FileObject,
        related_name="source_document_svgs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    sequence = models.PositiveIntegerField(null=False, blank=False)
    original_filename = models.CharField(max_length=500, null=False, blank=False)
    document_type = models.CharField(
        max_length=50, null=False, blank=True, default=""
    )
    status = models.IntegerField(
        default=SourceDocumentStatusEnum.UPLOADED.value,
        null=False,
        blank=False,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, null=False, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="uploaded_source_documents",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_source_documents",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "source_document"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["work_item", "sequence"],
                name="uq_workitem_source_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["work_item", "status"],
                name="idx_source_workitem_status",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_item.item_code} - Source {self.sequence}: "
            f"{self.original_filename}"
        )


class Part(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    source_document = models.ForeignKey(
        SourceDocument,
        related_name="parts",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    sequence = models.PositiveIntegerField(null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=True, default="")
    status = models.IntegerField(
        default=PartStatusEnum.NEW.value,
        null=False,
        blank=False,
        db_index=True,
    )
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_bbox = models.JSONField(default=dict, null=False, blank=True)
    preview_file = models.ForeignKey(
        FileObject,
        null=True,
        blank=True,
        related_name="part_previews",
        on_delete=models.SET_NULL,
    )
    detected_metadata = models.JSONField(default=dict, null=False, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_parts",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_parts",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "part"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_document", "sequence"],
                name="uq_source_part_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["source_document", "status"],
                name="idx_part_source_status",
            ),
        ]

    @property
    def work_item(self):
        return self.source_document.work_item

    def __str__(self):
        return f"{self.source_document} - Part {self.sequence}"


class WorkflowStepDefinition(TimeStampedModel):
    id = models.SmallAutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True, null=False, blank=False)
    sequence = models.PositiveSmallIntegerField(unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1, null=False, blank=False)
    is_active = models.BooleanField(null=False, default=True)
    settings_schema_key = models.CharField(
        max_length=100, null=False, blank=True, default=""
    )

    class Meta:
        db_table = "workflow_step_definition"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.sequence}. {self.name}"


class WorkflowTemplate(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    code = models.CharField(max_length=100, unique=True, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(null=False, default=True)
    is_default = models.BooleanField(null=False, default=False)

    class Meta:
        db_table = "workflow_template"
        ordering = ["code"]

    def __str__(self):
        return self.code


class TemplateStep(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        related_name="template_steps",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    step = models.ForeignKey(
        WorkflowStepDefinition,
        related_name="template_steps",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    sequence = models.PositiveSmallIntegerField(null=False, blank=False)
    is_required = models.BooleanField(null=False, default=True)
    settings_schema_version = models.PositiveIntegerField(
        default=1, null=False, blank=False
    )

    class Meta:
        db_table = "template_step"
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "step"],
                name="uq_template_step",
            ),
            models.UniqueConstraint(
                fields=["template", "sequence"],
                name="uq_template_sequence",
            ),
        ]

    def __str__(self):
        return f"{self.template.code} - {self.step.code}"


class PartStep(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    part = models.ForeignKey(
        Part,
        related_name="steps",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    step = models.ForeignKey(
        WorkflowStepDefinition,
        related_name="part_steps",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    status = models.IntegerField(
        default=StepStatusEnum.NOT_STARTED.value,
        null=False,
        blank=False,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    latest_revision = models.ForeignKey(
        "StepRevision",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    official_revision = models.ForeignKey(
        "StepRevision",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_part_steps",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "part_step"
        constraints = [
            models.UniqueConstraint(
                fields=["part", "step"],
                name="uq_part_step",
            ),
        ]
        indexes = [
            models.Index(
                fields=["part", "status"],
                name="idx_partstep_part_status",
            ),
        ]

    def __str__(self):
        return f"{self.part} - {self.step}"


class StepRevision(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    part_step = models.ForeignKey(
        PartStep,
        related_name="revisions",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    revision_no = models.PositiveIntegerField(null=False, blank=False)
    revision_type = models.IntegerField(
        default=RevisionTypeEnum.MANUAL.value,
        null=False,
        blank=False,
        db_index=True,
    )
    parent_revision = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="child_revisions",
        on_delete=models.SET_NULL,
    )
    settings = models.JSONField(default=dict, null=False, blank=True)
    settings_schema_version = models.PositiveIntegerField(
        default=1, null=False, blank=False
    )
    app_version = models.CharField(max_length=50, null=False, blank=True, default="")
    settings_hash = models.CharField(
        max_length=64, null=False, blank=True, default="", db_index=True
    )
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_step_revisions",
        on_delete=models.SET_NULL,
    )
    note = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "step_revision"
        ordering = ["-revision_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["part_step", "revision_no"],
                name="uq_partstep_revision_no",
            ),
        ]
        indexes = [
            models.Index(
                fields=["part_step", "-created"],
                name="idx_revision_latest",
            ),
            models.Index(
                fields=["part_step", "revision_type"],
                name="idx_revision_type",
            ),
        ]

    def __str__(self):
        return f"{self.part_step} - Revision {self.revision_no}"


class RevisionArtifact(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    revision = models.ForeignKey(
        StepRevision,
        related_name="artifacts",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    file = models.ForeignKey(
        FileObject,
        related_name="revision_artifacts",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    filename = models.CharField(max_length=500, null=False, blank=True, default="")
    role = models.CharField(max_length=100, null=False, blank=False, db_index=True)
    sequence = models.PositiveIntegerField(default=0, null=False, blank=False)
    metadata = models.JSONField(default=dict, null=False, blank=True)

    class Meta:
        db_table = "revision_artifact"
        ordering = ["role", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "role", "sequence"],
                name="uq_revision_artifact_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["revision", "role"],
                name="idx_artifact_revision_role",
            ),
        ]

    def __str__(self):
        return f"{self.revision} - {self.role} #{self.sequence}"


class DesignWorkspace(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    part_step = models.OneToOneField(
        PartStep,
        related_name="design_workspace",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    settings = models.JSONField(default=dict, null=False, blank=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_design_workspaces",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "design_workspace"

    def __str__(self):
        return f"Workspace for {self.part_step}"


class DesignFile(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    workspace = models.ForeignKey(
        DesignWorkspace,
        related_name="files",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    file_type = models.CharField(max_length=10, null=False, blank=False, db_index=True)
    latest_revision = models.ForeignKey(
        "DesignFileRevision",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    official_revision = models.ForeignKey(
        "DesignFileRevision",
        null=True,
        blank=True,
        related_name="+",
        on_delete=models.SET_NULL,
    )
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="updated_design_files",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "design_file"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "file_type"],
                name="uq_design_file_type",
            ),
        ]

    def __str__(self):
        return f"{self.workspace} - {self.file_type}"


class DesignFileRevision(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    design_file = models.ForeignKey(
        DesignFile,
        related_name="revisions",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    revision_no = models.PositiveIntegerField(null=False, blank=False)
    revision_type = models.IntegerField(
        default=RevisionTypeEnum.MANUAL.value,
        null=False,
        blank=False,
        db_index=True,
    )
    parent_revision = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="child_revisions",
        on_delete=models.SET_NULL,
    )
    layers = models.JSONField(default=list, null=False, blank=True)
    grid_width = models.PositiveIntegerField(default=0, null=False, blank=False)
    grid_height = models.PositiveIntegerField(default=0, null=False, blank=False)
    snapshot_file = models.ForeignKey(
        FileObject,
        related_name="design_file_snapshots",
        on_delete=models.PROTECT,
        null=False,
        blank=False,
    )
    preview_file = models.ForeignKey(
        FileObject,
        null=True,
        blank=True,
        related_name="design_file_previews",
        on_delete=models.SET_NULL,
    )
    tile_manifest = models.JSONField(default=dict, null=False, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_design_file_revisions",
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "design_file_revision"
        ordering = ["-revision_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["design_file", "revision_no"],
                name="uq_design_file_revision_no",
            ),
        ]

    def __str__(self):
        return f"DesignFileRevision {self.revision_no} ({self.design_file_id})"


class ColorDefinition(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    code = models.PositiveSmallIntegerField(unique=True, null=False, blank=False)
    hex_value = models.CharField(max_length=7, null=False, blank=False)
    name = models.CharField(max_length=100, null=False, blank=False)
    default_order = models.PositiveSmallIntegerField(default=0, null=False, blank=False)
    is_system = models.BooleanField(null=False, default=True)

    class Meta:
        db_table = "color_definition"
        ordering = ["default_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class UserColorPreference(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, null=False, blank=False
    )
    user = models.ForeignKey(
        User,
        related_name="color_preferences",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
    )
    color_definition = models.ForeignKey(
        ColorDefinition,
        null=True,
        blank=True,
        related_name="user_preferences",
        on_delete=models.CASCADE,
    )
    custom_hex = models.CharField(max_length=7, null=False, blank=True, default="")
    custom_name = models.CharField(max_length=100, null=False, blank=True, default="")
    display_order = models.PositiveSmallIntegerField(default=0, null=False, blank=False)

    class Meta:
        db_table = "user_color_preference"
        ordering = ["display_order", "created"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "color_definition"],
                name="uq_user_color_definition",
                condition=models.Q(color_definition__isnull=False),
            ),
        ]

    def __str__(self):
        label = self.custom_name or (self.color_definition.name if self.color_definition else "")
        return f"{self.user} - {label}"


class Notification(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notify_type = models.IntegerField(default=1, null=False, blank=False)
    data = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(null=False, default=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created"]

    def __str__(self):
        return f"Notification for {self.user_id} - {self.notify_type}"
