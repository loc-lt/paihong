from datetime import date

from django_filters import rest_framework as filters

from core.models import Notification, Part, SourceDocument, StepRevision, WorkItem


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
