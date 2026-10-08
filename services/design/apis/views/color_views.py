from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError

from core.filters import ColorDefinitionFilter, UserColorPreferenceFilter
from core.models import ColorDefinition, UserColorPreference
from core.permissions import require_design, require_system_color_admin
from core.responses import success_response
from core.serializers.color_serializers import (
    ColorDefinitionSerializer,
    MergedColorSerializer,
    SystemColorWriteSerializer,
    UserColorPreferenceCreateSerializer,
    UserColorPreferenceUpdateSerializer,
)
from core.services.color_palette import build_merged_palette, preference_to_merged_entry
from core.utils import get_instance, global_response_errors

from ..documents.color_documents import (
    create_system_color_document,
    create_user_color_document,
    delete_system_color_document,
    delete_user_color_document,
    get_system_color_document,
    list_colors_document,
    list_system_colors_document,
    update_system_color_document,
    update_user_color_document,
)


def _get_custom_color(user, pk):
    if ColorDefinition.objects.filter(pk=pk).exists():
        raise ValidationError(
            {"id": "System colors cannot be changed here! Use /system_colors instead."}
        )
    pref = UserColorPreference.objects.filter(pk=pk, user=user).first()
    if not pref:
        raise NotFound("User color not found!")
    return pref


class ColorViewSet(viewsets.ViewSet):
    @extend_schema(**list_colors_document)
    def list(self, request):
        system_colors = ColorDefinitionFilter(
            request.query_params,
            queryset=ColorDefinition.objects.filter(is_system=True),
        ).qs
        custom_colors = UserColorPreferenceFilter(
            request.query_params,
            queryset=UserColorPreference.objects.filter(user=request.user),
        ).qs
        merged = build_merged_palette(system_colors, custom_colors)
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
            return success_response(
                MergedColorSerializer(preference_to_merged_entry(pref)).data,
                "User color created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**update_user_color_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
        try:
            pref = _get_custom_color(request.user, pk)
        except ValidationError as exc:
            return global_response_errors(exc.detail)
        serializer = UserColorPreferenceUpdateSerializer(
            pref,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            pref = serializer.save()
            return success_response(
                MergedColorSerializer(preference_to_merged_entry(pref)).data,
                "User color updated successfully!",
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**delete_user_color_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        try:
            pref = _get_custom_color(request.user, pk)
        except ValidationError as exc:
            return global_response_errors(exc.detail)
        pref.delete()
        return success_response({}, "User color deleted successfully!")


class SystemColorViewSet(viewsets.ViewSet):
    @extend_schema(**list_system_colors_document)
    def list(self, request):
        colors = ColorDefinitionFilter(
            request.query_params,
            queryset=ColorDefinition.objects.filter(is_system=True).order_by(
                "display_order", "code"
            ),
        ).qs
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

    @extend_schema(**create_system_color_document)
    def create(self, request):
        require_system_color_admin(request.user)
        serializer = SystemColorWriteSerializer(data=request.data)
        if serializer.is_valid():
            color = serializer.save()
            return success_response(
                ColorDefinitionSerializer(color).data,
                "System color created successfully!",
                status.HTTP_201_CREATED,
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**update_system_color_document)
    def partial_update(self, request, pk=None):
        require_system_color_admin(request.user)
        color = get_instance(ColorDefinition, pk)
        serializer = SystemColorWriteSerializer(color, data=request.data, partial=True)
        if serializer.is_valid():
            color = serializer.save()
            return success_response(
                ColorDefinitionSerializer(color).data,
                "System color updated successfully!",
            )
        return global_response_errors(serializer.errors)

    @extend_schema(**delete_system_color_document)
    def destroy(self, request, pk=None):
        require_system_color_admin(request.user)
        color = get_instance(ColorDefinition, pk)
        color.delete()
        return success_response({}, "System color deleted successfully!")
