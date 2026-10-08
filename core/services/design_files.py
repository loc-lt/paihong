"""Design workspace file types and display naming for step 10."""

from __future__ import annotations

DESIGN_FILE_SEQUENCE = ("S", "S1", "C", "H", "P", "F", "FC", "KMO")

# File types that use grid snapshot + PATCH/GET tiles API.
GRID_DESIGN_FILE_TYPES = frozenset(DESIGN_FILE_SEQUENCE)

DESIGN_FILE_SPECS: dict[str, dict[str, str | bool]] = {
    "S": {"filename_template": "{product_code}_S.png", "grid": True},
    "S1": {"filename_template": "{product_code}_S1.png", "grid": True},
    "C": {"filename_template": "{product_code}_C.png", "grid": True},
    "H": {"filename_template": "{product_code}_H.png", "grid": True},
    "P": {"filename_template": "{product_code}_P.png", "grid": True},
    "F": {"filename_template": "{product_code}_F.png", "grid": True},
    "FC": {"filename_template": "{product_code}_FC.png", "grid": True},
    "KMO": {"filename_template": "{product_code}.kmo", "grid": True},
}


def build_design_file_display_name(product_code: str, file_type: str, name: str = "") -> str:
    if name:
        return name
    if file_type not in DESIGN_FILE_SPECS:
        raise ValueError(f"Unknown design file type: {file_type}")
    template = str(DESIGN_FILE_SPECS[file_type]["filename_template"])
    code = (product_code or "").strip() or "PRODUCT"
    return template.format(product_code=code)


def is_draft_design_file_type(file_type: str) -> bool:
    suffix = file_type[1:]
    return file_type.startswith("D") and suffix.isdigit()


def is_grid_design_file(file_type: str) -> bool:
    return file_type in GRID_DESIGN_FILE_TYPES or is_draft_design_file_type(file_type)


def validate_design_file_complete_order(*, workspace, file_type: str) -> None:
    """Require all prior files in DESIGN_FILE_SEQUENCE to be done before completing."""
    from rest_framework.exceptions import ValidationError

    if file_type not in DESIGN_FILE_SEQUENCE:
        raise ValidationError({"file_type": f"Unknown design file type: {file_type}!"})

    progress = dict((workspace.settings or {}).get("progress") or {})
    index = DESIGN_FILE_SEQUENCE.index(file_type)
    for prev_type in DESIGN_FILE_SEQUENCE[:index]:
        if progress.get(prev_type) != "done":
            raise ValidationError({"file_type": f"Complete {prev_type} before {file_type}!"})
