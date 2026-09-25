from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound

from core.models import ColorDefinition, UserColorPreference
from core.permissions import require_design
from core.responses import success_response
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceUpdateSerializer,
)
from core.services.color_palette import build_merged_palette, preference_to_merged_entry
from core.utils import get_instance, global_response_errors

from ..documents.color_documents import (
    create_user_color_document,
    delete_user_color_document,
    get_system_color_document,
    list_colors_document,
    list_system_colors_document,
    update_user_color_document,
)

class ColorViewSet(viewsets.ViewSet):
    @extend_schema(**list_colors_document)
    def list(self, request):
        merged = build_merged_palette(request.user)
        return success_response(
            MergedColorSerializer(merged, many=True).data,
            "Colors retrieved successfully!",
        )

    @extend_schema(**create_user_color_document)
    def create(self, request):
        require_design(request.user)
        serializer = UserColorPreferenceCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if serializer.is_valid():
            pref = serializer.save()
            if pref.color_definition_id:
                pref = UserColorPreference.objects.select_related("color_definition").get(
                    pk=pref.pk
                )
            return success_response(
                MergedColorSerializer(preference_to_merged_entry(pref)).data,
                "User color created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**update_user_color_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
        pref = UserColorPreference.objects.filter(pk=pk, user=request.user).first()
        if not pref:
            raise NotFound("User color preference not found!")
        serializer = UserColorPreferenceUpdateSerializer(
            pref, data=request.data, partial=True
        )
        if serializer.is_valid():
            pref = serializer.save()
            if pref.color_definition_id:
                pref = UserColorPreference.objects.select_related("color_definition").get(
                    pk=pref.pk
                )
            return success_response(
                MergedColorSerializer(preference_to_merged_entry(pref)).data,
                "User color updated successfully!",
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**delete_user_color_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        pref = UserColorPreference.objects.filter(pk=pk, user=request.user).first()
        if not pref:
            raise NotFound("User color preference not found!")
        pref.delete()
        return success_response({}, "User color deleted successfully!")

class SystemColorViewSet(viewsets.ViewSet):
    @extend_schema(**list_system_colors_document)
    def list(self, request):
        colors = ColorDefinition.objects.filter(is_system=True).order_by(
            "default_order", "code"
        )
        return success_response(
            ColorDefinitionSerializer(colors, many=True).data,
            "System colors retrieved successfully!",
        )

    @extend_schema(**get_system_color_document)
    def retrieve(self, request, pk=None):
        color = get_instance(ColorDefinition, pk)
        return success_response(
            ColorDefinitionSerializer(color).data,
            "System color retrieved successfully!",
        )
