from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound

from core.models import ColorDefinition, UserColorPreference
from core.permissions import require_design
from core.responses import success_response
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceSerializer,
)
from core.utils import get_instance, global_response_errors


class ColorViewSet(viewsets.ViewSet):
    def list(self, request):
        system_colors = ColorDefinition.objects.filter(is_system=True).order_by(
            "default_order", "code"
        )
        user_prefs = UserColorPreference.objects.filter(user=request.user).select_related(
            "color_definition"
        )

        merged = []
        seen_system_ids = set()
        for pref in user_prefs:
            if pref.color_definition_id:
                seen_system_ids.add(pref.color_definition_id)
                merged.append(
                    {
                        "id": pref.id,
                        "code": pref.color_definition.code,
                        "hex_value": pref.custom_hex or pref.color_definition.hex_value,
                        "name": pref.custom_name or pref.color_definition.name,
                        "display_order": pref.display_order,
                        "is_system": True,
                        "is_custom": bool(pref.custom_hex or pref.custom_name),
                    }
                )
            else:
                merged.append(
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

        for color in system_colors:
            if color.id in seen_system_ids:
                continue
            merged.append(
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

        merged.sort(key=lambda item: (item["display_order"], item.get("code") or 0))
        return success_response(
            MergedColorSerializer(merged, many=True).data,
            "Colors retrieved successfully!",
        )

    def create(self, request):
        require_design(request.user)
        serializer = UserColorPreferenceCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            pref = serializer.save()
            return success_response(
                UserColorPreferenceSerializer(pref).data,
                "User color created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    def destroy(self, request, pk=None):
        require_design(request.user)
        pref = UserColorPreference.objects.filter(pk=pk, user=request.user).first()
        if not pref:
            raise NotFound("User color preference not found!")
        pref.delete()
        return success_response({}, "User color deleted successfully!")


class SystemColorViewSet(viewsets.ViewSet):
    def list(self, request):
        colors = ColorDefinition.objects.filter(is_system=True).order_by(
            "default_order", "code"
        )
        return success_response(
            ColorDefinitionSerializer(colors, many=True).data,
            "System colors retrieved successfully!",
        )

    def retrieve(self, request, pk=None):
        color = get_instance(ColorDefinition, pk)
        return success_response(
            ColorDefinitionSerializer(color).data,
            "System color retrieved successfully!",
        )
