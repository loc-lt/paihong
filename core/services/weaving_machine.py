"""Catalog of weaving machines: name + gauge + width, and barre rows per name."""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from core.models import WeavingMachine, WeavingMachineBar, WeavingMachineSpec

_MISSING = object()


def machine_detail_queryset():
    return WeavingMachine.objects.prefetch_related("specs", "bars")


def _reject_duplicate(queryset, message_field: str, message: str) -> None:
    if queryset.exists():
        raise ValidationError({message_field: message})


@transaction.atomic
def create_machine(
    *,
    name: str,
    type: str,
    jacquard: int,
    max_bars: int = 0,
    bars=None,
) -> WeavingMachine:
    _reject_duplicate(
        WeavingMachine.objects.filter(name=name),
        "name",
        "Machine name already exists!",
    )
    machine = WeavingMachine.objects.create(
        name=name,
        type=type,
        jacquard=jacquard,
        max_bars=max_bars,
    )
    if bars is not None:
        _replace_bars(machine, bars)
    return machine


@transaction.atomic
def update_machine(
    machine: WeavingMachine,
    *,
    name: str | None = None,
    type: str | None = None,
    jacquard: int | None = None,
    max_bars: int | None = None,
    bars=_MISSING,
) -> WeavingMachine:
    update_fields = []
    if name is not None and name != machine.name:
        _reject_duplicate(
            WeavingMachine.objects.filter(name=name).exclude(pk=machine.pk),
            "name",
            "Machine name already exists!",
        )
        machine.name = name
        update_fields.append("name")
    if type is not None and type != machine.type:
        machine.type = type
        update_fields.append("type")
    if jacquard is not None and jacquard != machine.jacquard:
        machine.jacquard = jacquard
        update_fields.append("jacquard")
    if max_bars is not None and max_bars != machine.max_bars:
        machine.max_bars = max_bars
        update_fields.append("max_bars")
    if update_fields:
        update_fields.append("modified")
        machine.save(update_fields=update_fields)
    if bars is not _MISSING:
        _replace_bars(machine, bars or [])
    return machine


@transaction.atomic
def delete_machine(machine: WeavingMachine) -> None:
    machine.delete()


@transaction.atomic
def create_spec(machine: WeavingMachine, *, needles_per_inch, width) -> WeavingMachineSpec:
    _reject_duplicate(
        machine.specs.filter(needles_per_inch=needles_per_inch, width=width),
        "width",
        "This gauge and width already exist for the machine!",
    )
    return WeavingMachineSpec.objects.create(
        machine=machine,
        needles_per_inch=needles_per_inch,
        width=width,
    )


@transaction.atomic
def update_spec(spec: WeavingMachineSpec, **fields) -> WeavingMachineSpec:
    needles = fields.get("needles_per_inch", spec.needles_per_inch)
    width = fields.get("width", spec.width)
    if needles != spec.needles_per_inch or width != spec.width:
        _reject_duplicate(
            spec.machine.specs.filter(needles_per_inch=needles, width=width).exclude(pk=spec.pk),
            "width",
            "This gauge and width already exist for the machine!",
        )
    _assign(spec, fields)
    return spec


@transaction.atomic
def delete_spec(spec: WeavingMachineSpec) -> None:
    spec.delete()


@transaction.atomic
def create_bar(machine: WeavingMachine, **fields) -> WeavingMachineBar:
    _reject_duplicate(
        machine.bars.filter(bar_no=fields["bar_no"]),
        "bar_no",
        "This bar number already exists on the machine!",
    )
    return WeavingMachineBar.objects.create(machine=machine, **fields)


@transaction.atomic
def update_bar(bar: WeavingMachineBar, **fields) -> WeavingMachineBar:
    bar_no = fields.get("bar_no", _MISSING)
    if bar_no is not _MISSING and bar_no != bar.bar_no:
        _reject_duplicate(
            bar.machine.bars.filter(bar_no=bar_no).exclude(pk=bar.pk),
            "bar_no",
            "This bar number already exists on the machine!",
        )
    _assign(bar, fields)
    return bar


@transaction.atomic
def delete_bar(bar: WeavingMachineBar) -> None:
    bar.delete()


def _assign(instance, fields: dict) -> None:
    update_fields = []
    for key, value in fields.items():
        if getattr(instance, key) != value:
            setattr(instance, key, value)
            update_fields.append(key)
    if update_fields:
        update_fields.append("modified")
        instance.save(update_fields=update_fields)


def _replace_bars(machine: WeavingMachine, bars: list[dict]) -> None:
    seen = set()
    for item in bars:
        bar_no = item["bar_no"]
        if bar_no in seen:
            raise ValidationError({"bar_no": f"Bar {bar_no} is duplicated!"})
        seen.add(bar_no)
    machine.bars.all().delete()
    for item in bars:
        WeavingMachineBar.objects.create(machine=machine, **item)
