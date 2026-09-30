from __future__ import annotations

from core.models import ColorDefinition, UserColorPreference


def build_merged_palette(user) -> list[dict]:
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
        }
        for color in ColorDefinition.objects.filter(is_system=True).order_by(
            "display_order", "code"
        )
    ]

    custom_entries = [
        preference_to_merged_entry(pref)
        for pref in UserColorPreference.objects.filter(user=user).order_by(
            "display_order", "created"
        )
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
    }


def custom_code_exists(*, user, code: int, exclude_pk=None) -> bool:
    queryset = UserColorPreference.objects.filter(user=user, code=code)
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


def custom_hex_exists(*, user, hex_value: str, exclude_pk=None) -> bool:
    if ColorDefinition.objects.filter(
        is_system=True, hex_value__iexact=hex_value
    ).exists():
        return True
    queryset = UserColorPreference.objects.filter(
        user=user, custom_hex__iexact=hex_value
    )
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()
