from __future__ import annotations

from core.models import ColorDefinition, UserColorPreference


def build_merged_palette(user) -> list[dict]:
    """Merge system palette + user customs. System order is fixed (default_order)."""
    system_colors = ColorDefinition.objects.filter(is_system=True).order_by(
        "default_order", "code"
    )
    user_prefs = UserColorPreference.objects.filter(user=user).select_related(
        "color_definition"
    )

    override_by_system_id = {
        pref.color_definition_id: pref
        for pref in user_prefs
        if pref.color_definition_id
    }

    system_entries: list[dict] = []
    for color in system_colors:
        pref = override_by_system_id.get(color.id)
        if pref:
            system_entries.append(
                {
                    "id": pref.id,
                    "code": color.code,
                    "hex_value": pref.custom_hex or color.hex_value,
                    "name": pref.custom_name or color.name,
                    "display_order": color.default_order,
                    "is_system": True,
                    "is_custom": bool(pref.custom_hex or pref.custom_name),
                }
            )
        else:
            system_entries.append(
                {
                    "id": color.id,
                    "code": color.code,
                    "hex_value": color.hex_value,
                    "name": color.name,
                    "display_order": color.default_order,
                    "is_system": True,
                    "is_custom": False,
                }
            )

    custom_entries: list[dict] = []
    for pref in sorted(user_prefs, key=lambda item: (item.display_order, item.created)):
        if pref.color_definition_id:
            continue
        custom_entries.append(
            {
                "id": pref.id,
                "code": None,
                "hex_value": pref.custom_hex,
                "name": pref.custom_name,
                "display_order": pref.display_order,
                "is_system": False,
                "is_custom": True,
            }
        )

    return system_entries + custom_entries


def preference_to_merged_entry(pref: UserColorPreference) -> dict:
    """Single palette row — same shape as GET /colors items."""
    if pref.color_definition_id:
        color = pref.color_definition
        return {
            "id": pref.id,
            "code": color.code,
            "hex_value": pref.custom_hex or color.hex_value,
            "name": pref.custom_name or color.name,
            "display_order": color.default_order,
            "is_system": True,
            "is_custom": bool(pref.custom_hex or pref.custom_name),
        }
    return {
        "id": pref.id,
        "code": None,
        "hex_value": pref.custom_hex,
        "name": pref.custom_name,
        "display_order": pref.display_order,
        "is_system": False,
        "is_custom": True,
    }
