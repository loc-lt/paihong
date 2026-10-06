from drf_spectacular.utils import OpenApiParameter, OpenApiResponse

from core.serializers.weaving_machine_serializers import (
    BarWriteSerializer,
    MachineWriteSerializer,
    SpecWriteSerializer,
    WeavingMachineBarSerializer,
    WeavingMachineSerializer,
    WeavingMachineSpecSerializer,
    WeavingMachineSummarySerializer,
)

_DELETED = {200: OpenApiResponse(description="Deleted")}
_GAUGE_QUERY = OpenApiParameter(
    name="needles_per_inch",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="When set, only widths of this gauge (n/inch) are returned.",
)

list_machines_document = {
    "summary": "List weaving machines.",
    "responses": {200: WeavingMachineSummarySerializer(many=True)},
}
create_machine_document = {
    "summary": "Create a weaving machine.",
    "description": (
        "`type` is Single or Double. `jacquard` is 1 or 2. "
        "Optional `max_bars` and `bars` (the barre table for this machine name)."
    ),
    "request": MachineWriteSerializer,
    "responses": {201: WeavingMachineSerializer},
}
get_machine_document = {
    "summary": "Get a machine, its gauge/width rows, max_bars, and barre table.",
    "responses": {200: WeavingMachineSerializer},
}
update_machine_document = {
    "summary": "Update name, machine type, jacquard, max_bars, or replace the barre table.",
    "description": "Sending `bars` replaces every barre row of this machine name.",
    "request": MachineWriteSerializer,
    "responses": {200: WeavingMachineSerializer},
}
delete_machine_document = {
    "summary": "Delete a machine, its gauge/width rows, and its barres.",
    "responses": _DELETED,
}
list_specs_document = {
    "summary": "List gauge + width rows of one machine.",
    "description": (
        "Path `{id}` is the weaving machine. Without a query, every gauge and width "
        "of that machine is returned. Pass `needles_per_inch` to list only the widths "
        "of that gauge on that machine. Gauge is not unique across machines."
    ),
    "parameters": [_GAUGE_QUERY],
    "responses": {200: WeavingMachineSpecSerializer(many=True)},
}
create_spec_document = {
    "summary": "Add one gauge + width for a machine name.",
    "request": SpecWriteSerializer,
    "responses": {201: WeavingMachineSpecSerializer},
}
get_spec_document = {
    "summary": "Get one gauge + width row.",
    "responses": {200: WeavingMachineSpecSerializer},
}
update_spec_document = {
    "summary": "Update gauge or width of one row.",
    "request": SpecWriteSerializer,
    "responses": {200: WeavingMachineSpecSerializer},
}
delete_spec_document = {
    "summary": "Delete one gauge + width row.",
    "responses": _DELETED,
}
list_bars_document = {
    "summary": "List barre rows of one machine.",
    "description": "Path `{id}` is the weaving machine. Barre rows belong to that machine name.",
    "responses": {200: WeavingMachineBarSerializer(many=True)},
}
create_bar_document = {
    "summary": "Add one barre row.",
    "request": BarWriteSerializer,
    "responses": {201: WeavingMachineBarSerializer},
}
get_bar_document = {
    "summary": "Get one barre row.",
    "responses": {200: WeavingMachineBarSerializer},
}
update_bar_document = {
    "summary": "Update one barre row.",
    "request": BarWriteSerializer,
    "responses": {200: WeavingMachineBarSerializer},
}
delete_bar_document = {
    "summary": "Delete one barre row.",
    "responses": _DELETED,
}
