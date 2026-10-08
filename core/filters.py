from datetime import date

from django_filters import rest_framework as filters

from core.models import (
    ColorDefinition,
    Notification,
    Part,
    SourceDocument,
    StepRevision,
    UserColorPreference,
    WorkItem,
)


class NotificationFilter(filters.FilterSet):
    class Meta:
        model = Notification
        fields = {"is_read": ["exact"]}


class WorkItemFilter(filters.FilterSet):
    item_code = filters.CharFilter(field_name="item_code", lookup_expr="icontains")
    status = filters.NumberFilter(field_name="status")
    q = filters.CharFilter(method="filter_q")

    class Meta:
        model = WorkItem
        fields = ["item_code", "status", "q"]

    def filter_q(self, queryset, name, value):
        query = (value or "").strip()
        if not query:
            return queryset
        return queryset.filter(item_code__icontains=query)


class SourceDocumentFilter(filters.FilterSet):
    status = filters.NumberFilter(field_name="status")

    class Meta:
        model = SourceDocument
        fields = ["status"]


class PartFilter(filters.FilterSet):
    status = filters.NumberFilter(field_name="status")

    class Meta:
        model = Part
        fields = ["status"]


def _parse_filter_date(value):
    text = (value or "").strip()
    if not text:
        return None, True
    try:
        return date.fromisoformat(text), True
    except ValueError:
        return None, False


class StartDesigningPartFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q")
    created_from = filters.CharFilter(method="filter_created_from")
    created_to = filters.CharFilter(method="filter_created_to")

    class Meta:
        model = Part
        fields = ["q", "created_from", "created_to"]

    def filter_q(self, queryset, name, value):
        query = (value or "").strip()
        if not query:
            return queryset
        return queryset.filter(name__icontains=query)

    def filter_created_from(self, queryset, name, value):
        parsed, ok = _parse_filter_date(value)
        if not ok:
            return queryset.none()
        if parsed is None:
            return queryset
        return queryset.filter(created__date__gte=parsed)

    def filter_created_to(self, queryset, name, value):
        parsed, ok = _parse_filter_date(value)
        if not ok:
            return queryset.none()
        if parsed is None:
            return queryset
        return queryset.filter(created__date__lte=parsed)


class StepRevisionFilter(filters.FilterSet):
    revision_type = filters.NumberFilter(field_name="revision_type")

    class Meta:
        model = StepRevision
        fields = ["revision_type"]


def _parse_filter_bool(value):
    text = (value or "").strip().lower()
    if not text:
        return None, True
    if text in {"true", "1"}:
        return True, True
    if text in {"false", "0"}:
        return False, True
    return None, False


def _apply_bool_filter(queryset, field_name, value):
    parsed, ok = _parse_filter_bool(value)
    if not ok:
        return queryset.none()
    if parsed is None:
        return queryset
    return queryset.filter(**{field_name: parsed})


class _ColorGroupFilterMixin:
    is_svg = filters.CharFilter(method="filter_is_svg")
    is_pixel = filters.CharFilter(method="filter_is_pixel")

    def filter_is_svg(self, queryset, name, value):
        return _apply_bool_filter(queryset, "is_svg", value)

    def filter_is_pixel(self, queryset, name, value):
        return _apply_bool_filter(queryset, "is_pixel", value)


class ColorDefinitionFilter(_ColorGroupFilterMixin, filters.FilterSet):
    class Meta:
        model = ColorDefinition
        fields = ["is_svg", "is_pixel"]


class UserColorPreferenceFilter(_ColorGroupFilterMixin, filters.FilterSet):
    class Meta:
        model = UserColorPreference
        fields = ["is_svg", "is_pixel"]
