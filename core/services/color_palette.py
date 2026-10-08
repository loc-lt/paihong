from __future__ import annotations

from core.models import ColorDefinition, UserColorPreference


def build_merged_palette(system_colors, custom_colors) -> list[dict]:
    """System colors (read-only) + the current user's custom colors."""
    system_entries = [
        {
            "id": color.id,
            "code": color.code,
            "hex_value": color.hex_value,
            "name": color.name,
            "display_order": color.display_order,
            "is_system": True,
            "is_custom": False,
            "is_svg": color.is_svg,
            "is_pixel": color.is_pixel,
        }
        for color in system_colors.order_by("display_order", "code")
    ]

    custom_entries = [
        preference_to_merged_entry(pref)
        for pref in custom_colors.order_by("display_order", "created")
    ]
    return system_entries + custom_entries


def preference_to_merged_entry(pref: UserColorPreference) -> dict:
    return {
        "id": pref.id,
        "code": pref.code,
        "hex_value": pref.custom_hex,
        "name": pref.custom_name,
        "display_order": pref.display_order,
        "is_system": False,
        "is_custom": True,
        "is_svg": pref.is_svg,
        "is_pixel": pref.is_pixel,
    }


def custom_code_exists(
    *,
    user,
    code: int,
    is_svg: bool,
    is_pixel: bool,
    exclude_pk=None,
) -> bool:
    queryset = UserColorPreference.objects.filter(
        user=user,
        code=code,
        is_svg=is_svg,
        is_pixel=is_pixel,
    )
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def system_code_exists(*, code: int, exclude_pk=None) -> bool:
    queryset = ColorDefinition.objects.filter(code=code)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def system_hex_exists(*, hex_value: str, exclude_pk=None) -> bool:
    queryset = ColorDefinition.objects.filter(is_system=True, hex_value__iexact=hex_value)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def custom_hex_exists(
    *,
    user,
    hex_value: str,
    is_svg: bool,
    is_pixel: bool,
    exclude_pk=None,
) -> bool:
    system_colors = ColorDefinition.objects.filter(
        is_system=True, hex_value__iexact=hex_value
    )
    custom_colors = UserColorPreference.objects.filter(
        user=user, custom_hex__iexact=hex_value
    )
    if is_svg:
        system_colors = system_colors.filter(is_svg=True)
        custom_colors = custom_colors.filter(is_svg=True)
    if is_pixel:
        system_colors = system_colors.filter(is_pixel=True)
        custom_colors = custom_colors.filter(is_pixel=True)
    if exclude_pk:
        custom_colors = custom_colors.exclude(pk=exclude_pk)
    return system_colors.exists() or custom_colors.exists()
