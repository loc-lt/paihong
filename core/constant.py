from enum import Enum

from django.db.models import IntegerChoices


def choices_description(enum_cls, title):
    parts = ", ".join(f"{value} = {label}" for value, label in enum_cls.choices)
    return f"{title}: {parts}."


USER_DEFAULT_SYSTEM = None
MAX_IMAGE_SIZE = 50 * 1024 * 1024
AVATAR_MAX_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = ["png", "jpg", "jpeg", "webp"]
ALLOWED_SOURCE_EXTENSIONS = ["pdf", "ai", "dxf"]
ALLOWED_ARTIFACT_EXTENSIONS = [
    "png",
    "jpg",
    "jpeg",
    "json",
    "svg",
    "dxf",
    "pdf",
]
DEFAULT_OUTPUT_ARTIFACT_ROLE = "OUTPUT_IMAGE"
INTEGER_FIELD_MAX_VALUE = 2_147_483_647
BIG_INTEGER_FIELD_MAX_VALUE = 9_223_372_036_854_775_807
POSITIVE_SMALL_INTEGER_MAX_VALUE = 32_767
AUTOSAVE_KEEP_LATEST = 12

EXCLUDE_AUTH_PATH = [
    "api/v1/auth/login",
    "api/v1/auth/register",
    "api/v1/auth/refresh",
    "api/v1/auth/logout",
]

EXCLUDE_ACTIVE_PATH = [
    *EXCLUDE_AUTH_PATH,
    "api/v1/auth/logout",
    "api/v1/users/",
    "api/v1/auth/me/",
]

DIR_TO_UPLOAD_MAPPER = {"user": "pk"}

PERMISSIONS_LIST = []
UI_PERMISSION_MAPPING = {}


class UserRoleEnum(IntegerChoices):
    DEVELOPER = 1, "Developer"
    ADMIN = 2, "Admin"
    CUSTOMER = 3, "Customer"
    DESIGNER = 4, "Designer"


class UserStatusEnum(IntegerChoices):
    ACTIVE = 1, "Active"
    INACTIVE = 2, "Inactive"
    SUSPENDED = 3, "Suspended"


class StorageBackendEnum(IntegerChoices):
    LOCAL = 1, "Local filesystem"
    NAS = 2, "NAS"
    MINIO = 3, "MinIO"
    S3 = 4, "Amazon S3"


class WorkItemStatusEnum(IntegerChoices):
    NEW = 1, "New"
    PREPROCESSING = 2, "Pre-processing"
    DESIGNING = 3, "Designing"
    COMPLETED = 4, "Completed"
    FAILED = 5, "Failed"


class SourceDocumentStatusEnum(IntegerChoices):
    UPLOADED = 1, "Uploaded"
    PROCESSING = 2, "Processing"
    PROCESSED = 3, "Processed"
    FAILED = 4, "Failed"


class PartStatusEnum(IntegerChoices):
    NEW = 1, "New"
    PROCESSING = 2, "Processing"
    COMPLETED = 3, "Completed"
    FAILED = 4, "Failed"


class StepStatusEnum(IntegerChoices):
    NOT_STARTED = 1, "Not started"
    IN_PROGRESS = 2, "In progress"
    DONE = 3, "Done"


class RevisionTypeEnum(IntegerChoices):
    AUTOSAVE = 1, "Autosave"
    MANUAL = 2, "Manual save"
    OFFICIAL = 3, "Official save"
    RESTORE = 4, "Restore"


class NotificationTypeEnum(Enum):
    SYSTEM_NOTIFICATION = 1


STAFF_ROLES = (
    UserRoleEnum.DEVELOPER.value,
    UserRoleEnum.ADMIN.value,
    UserRoleEnum.DESIGNER.value,
)

# Temporary: all staff roles share the same access until fine-grained permissions.
ADMIN_ROLES = STAFF_ROLES
DESIGN_ROLES = STAFF_ROLES

USER_ROLE_DESCRIPTION = choices_description(UserRoleEnum, "User role")
USER_STATUS_DESCRIPTION = choices_description(UserStatusEnum, "User status")
WORK_ITEM_STATUS_DESCRIPTION = choices_description(
    WorkItemStatusEnum, "Work item status"
)
SOURCE_DOCUMENT_STATUS_DESCRIPTION = choices_description(
    SourceDocumentStatusEnum, "Source document status"
)
PART_STATUS_DESCRIPTION = choices_description(PartStatusEnum, "Part status")
STEP_STATUS_DESCRIPTION = choices_description(StepStatusEnum, "Step status")
REVISION_TYPE_DESCRIPTION = choices_description(RevisionTypeEnum, "Revision type")

BOOTSTRAP_DONE_STEP_CODES = ("RECEIVE_FILES")
WORKFLOW_ACTIVE_START_STEP_CODE = "ROTATE_STRIP_TEXT"

BOOTSTRAP_STEP_SETTINGS = {
    "PICK_UPPER": {
        "selected_candidate_index": 0,
        "rotation": 0.0,
        "candidates": [],
    },
}

DESIGN_FILE_SEQUENCE = ("S1", "C", "H", "SIM", "P", "FC", "F", "KMO")

GRID_TILE_SIZE = 256
GRID_SNAPSHOT_SCHEMA_VERSION = 1

STEP_SETTINGS_SOURCE_MANUAL = "manual"
STEP_SETTINGS_SOURCE_BOOTSTRAP = "bootstrap"
STEP_SETTINGS_SOURCE_PROPAGATED = "propagated"
STEP_SETTINGS_SOURCE_AI = "ai"
STEP_SETTINGS_SOURCE_RESTORED = "restored"
STEP_SETTINGS_SOURCE_GRID_IMPORT = "grid_import"

STEP_SETTINGS_POLICY = {
    "RECEIVE_FILES": {"has_settings": False},
    "PICK_UPPER": {
        "has_settings": True,
        "input_mode": "manual",
        "schema_key": "PICK_UPPER",
    },
    "ROTATE_STRIP_TEXT": {
        "has_settings": True,
        "input_mode": "manual",
    },
    "REMOVE_AUX_LINES": {
        "has_settings": True,
        "input_mode": "manual",
    },
    "FIX_LINES_BY_ANCHOR": {
        "has_settings": True,
        "input_mode": "manual",
        "schema_key": "FIX_LINES_BY_ANCHOR",
    },
    "CHECK_COLORS": {
        "has_settings": True,
        "input_mode": "manual",
        "schema_key": "CHECK_COLORS",
        "on_complete": {
            "propagate_to": "CANVAS_FRAME_MEASURE",
            "via": "ai",
        },
    },
    "CANVAS_FRAME_MEASURE": {
        "has_settings": True,
        "input_mode": "propagated_or_edit",
        "schema_key": "CANVAS_FRAME_MEASURE",
    },
    "ENTER_SPECS": {
        "has_settings": True,
        "input_mode": "manual",
        "schema_key": "ENTER_SPECS",
        "on_complete": {
            "propagate_to": "BUILD_GRID",
            "via": "propagated",
        },
    },
    "BUILD_GRID": {
        "has_settings": True,
        "input_mode": "manual",
        "schema_key": "BUILD_GRID",
        "on_complete": {
            "propagate_to": "START_DESIGNING",
            "via": "grid_import",
        },
    },
    "START_DESIGNING": {
        "has_settings": True,
        "input_mode": "grid_workspace",
        "schema_key": "START_DESIGNING",
    },
}

BOOTSTRAP_ARTIFACT_ROLES = {
    "RECEIVE_FILES": "SOURCE_FILE",
    "PICK_UPPER": "PREVIEW_IMAGE",
}

WORKFLOW_STEP_SEED = [
    (1, "RECEIVE_FILES", "Receive files"),
    (2, "PICK_UPPER", "Pick the upper"),
    (3, "ROTATE_STRIP_TEXT", "Rotate · strip text"),
    (4, "REMOVE_AUX_LINES", "Remove aux lines"),
    (5, "FIX_LINES_BY_ANCHOR", "Fix lines by anchor"),
    (6, "CHECK_COLORS", "Check colors"),
    (7, "CANVAS_FRAME_MEASURE", "Canvas frame · measure"),
    (8, "ENTER_SPECS", "Enter specs"),
    (9, "BUILD_GRID", "Build grid"),
    (10, "START_DESIGNING", "Start designing"),
]

STEP_SETTINGS_SCHEMAS = {
    "PICK_UPPER": "StepPickUpperSettingsSerializer",
    "FIX_LINES_BY_ANCHOR": "StepFixLinesByAnchorSettingsSerializer",
    "CHECK_COLORS": "StepCheckColorsSettingsSerializer",
    "CANVAS_FRAME_MEASURE": "StepCanvasFrameSettingsSerializer",
    "ENTER_SPECS": "StepEnterSpecsSettingsSerializer",
    "BUILD_GRID": "StepBuildGridSettingsSerializer",
    "START_DESIGNING": "StepStartDesigningSettingsSerializer",
}
