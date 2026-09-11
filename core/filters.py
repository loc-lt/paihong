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


class StepRevisionFilter(filters.FilterSet):
    revision_type = filters.NumberFilter(field_name="revision_type")

    class Meta:
        model = StepRevision
        fields = ["revision_type"]
