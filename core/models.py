import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.IntegerField(default=UserRoleEnum.CUSTOMER.value, db_index=True)
    status = models.IntegerField(
        default=UserStatusEnum.ACTIVE.value,
        db_index=True,
    )
    avatar = models.ForeignKey(
        "FileObject",
        null=True,
        blank=True,
        related_name="user_avatars",
        on_delete=models.SET_NULL,
    )
    is_staff = models.BooleanField(default=False)
    token_version = models.UUIDField(default=uuid.uuid4)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_backend = models.IntegerField(
        default=StorageBackendEnum.LOCAL.value,
    )
    storage_key = models.CharField(max_length=1000, unique=True)
    extension = models.CharField(max_length=30, blank=True)
    mime_type = models.CharField(max_length=150, blank=True)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_code = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True)
    status = models.IntegerField(
        default=WorkItemStatusEnum.NEW.value,
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    work_item = models.ForeignKey(
        WorkItem,
        related_name="source_documents",
        on_delete=models.CASCADE,
    )
    file = models.ForeignKey(
        FileObject,
        related_name="source_documents",
        on_delete=models.PROTECT,
    )
    sequence = models.PositiveIntegerField()
    original_filename = models.CharField(max_length=500)
    document_type = models.CharField(max_length=50, blank=True)
    status = models.IntegerField(
        default=SourceDocumentStatusEnum.UPLOADED.value,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_document = models.ForeignKey(
        SourceDocument,
        related_name="parts",
        on_delete=models.CASCADE,
    )
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=255, blank=True)
    status = models.IntegerField(
        default=PartStatusEnum.NEW.value,
        db_index=True,
    )
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_bbox = models.JSONField(default=dict, blank=True)
    preview_file = models.ForeignKey(
        FileObject,
        null=True,
        blank=True,
        related_name="part_previews",
        on_delete=models.SET_NULL,
    )
    detected_metadata = models.JSONField(default=dict, blank=True)
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
    code = models.CharField(max_length=100, unique=True)
    sequence = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    settings_schema_key = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "workflow_step_definition"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.sequence}. {self.name}"


class WorkflowTemplate(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = "workflow_template"
        ordering = ["code"]

    def __str__(self):
        return self.code


class TemplateStep(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        WorkflowTemplate,
        related_name="template_steps",
        on_delete=models.CASCADE,
    )
    step = models.ForeignKey(
        WorkflowStepDefinition,
        related_name="template_steps",
        on_delete=models.PROTECT,
    )
    sequence = models.PositiveSmallIntegerField()
    is_required = models.BooleanField(default=True)
    settings_schema_version = models.PositiveIntegerField(default=1)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part = models.ForeignKey(
        Part,
        related_name="steps",
        on_delete=models.CASCADE,
    )
    step = models.ForeignKey(
        WorkflowStepDefinition,
        related_name="part_steps",
        on_delete=models.PROTECT,
    )
    status = models.IntegerField(
        default=StepStatusEnum.NOT_STARTED.value,
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    part_step = models.ForeignKey(
        PartStep,
        related_name="revisions",
        on_delete=models.CASCADE,
    )
    revision_no = models.PositiveIntegerField()
    revision_type = models.IntegerField(db_index=True)
    parent_revision = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="child_revisions",
        on_delete=models.SET_NULL,
    )
    settings = models.JSONField(default=dict, blank=True)
    settings_schema_version = models.PositiveIntegerField(default=1)
    app_version = models.CharField(max_length=50, blank=True)
    settings_hash = models.CharField(max_length=64, blank=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="created_step_revisions",
        on_delete=models.SET_NULL,
    )
    note = models.TextField(blank=True)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.ForeignKey(
        StepRevision,
        related_name="artifacts",
        on_delete=models.CASCADE,
    )
    file = models.ForeignKey(
        FileObject,
        related_name="revision_artifacts",
        on_delete=models.PROTECT,
    )
    filename = models.CharField(max_length=500, blank=True)
    role = models.CharField(max_length=100, db_index=True)
    sequence = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

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


class Notification(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notifications",
    )
    notify_type = models.IntegerField(default=1)
    data = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "notifications"
        ordering = ["-created"]

    def __str__(self):
        return f"Notification for {self.user_id} - {self.notify_type}"
