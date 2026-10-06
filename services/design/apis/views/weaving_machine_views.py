from decimal import Decimal, InvalidOperation

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from core.models import WeavingMachine, WeavingMachineBar, WeavingMachineSpec
from core.permissions import require_design
from core.responses import success_response
from core.serializers.weaving_machine_serializers import (
    BarUpdateSerializer,
    BarWriteSerializer,
    MachineUpdateSerializer,
    MachineWriteSerializer,
    SpecUpdateSerializer,
    SpecWriteSerializer,
    WeavingMachineBarSerializer,
    WeavingMachineSerializer,
    WeavingMachineSpecSerializer,
    WeavingMachineSummarySerializer,
)
from core.services.weaving_machine import (
    delete_bar,
    delete_machine,
    delete_spec,
    machine_detail_queryset,
)
from core.utils import get_instance, global_response_errors

from ..documents.weaving_machine_documents import (
    create_bar_document,
    create_machine_document,
    create_spec_document,
    delete_bar_document,
    delete_machine_document,
    delete_spec_document,
    get_bar_document,
    get_machine_document,
    get_spec_document,
    list_bars_document,
    list_machines_document,
    list_specs_document,
    update_bar_document,
    update_machine_document,
    update_spec_document,
)


def _saved(serializer, *, read_with, message, created=False):
    if not serializer.is_valid():
        return global_response_errors(serializer.errors)
    try:
        instance = serializer.save()
    except ValidationError as exc:
        return global_response_errors(exc.detail)
    return success_response(
        read_with(instance).data,
        message,
        status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


def _detail(machine):
    return WeavingMachineSerializer(machine_detail_queryset().get(pk=machine.pk))


class WeavingMachineViewSet(viewsets.ViewSet):
    @extend_schema(**list_machines_document)
    def list(self, request):
        return success_response(
            WeavingMachineSummarySerializer(WeavingMachine.objects.all(), many=True).data,
            "Weaving machines retrieved successfully!",
        )

    @extend_schema(**create_machine_document)
    def create(self, request):
        require_design(request.user)
        return _saved(
            MachineWriteSerializer(data=request.data),
            read_with=_detail,
            message="Weaving machine created successfully!",
            created=True,
        )

    @extend_schema(**get_machine_document)
    def retrieve(self, request, pk=None):
        machine = get_instance(machine_detail_queryset(), pk)
        return success_response(
            WeavingMachineSerializer(machine).data,
            "Weaving machine retrieved successfully!",
        )

    @extend_schema(**update_machine_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
        machine = get_instance(WeavingMachine, pk)
        return _saved(
            MachineUpdateSerializer(machine, data=request.data, partial=True),
            read_with=_detail,
            message="Weaving machine updated successfully!",
        )

    @extend_schema(**delete_machine_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        machine = get_instance(WeavingMachine, pk)
        delete_machine(machine)
        return success_response(None, "Weaving machine deleted successfully!")

    @extend_schema(methods=["GET"], **list_specs_document)
    @extend_schema(methods=["POST"], **create_spec_document)
    @action(detail=True, methods=["get", "post"], url_path="specs")
    def specs(self, request, pk=None):
        machine = get_instance(WeavingMachine, pk)
        if request.method == "GET":
            specs = machine.specs.all()
            gauge = request.query_params.get("needles_per_inch")
            if gauge not in (None, ""):
                try:
                    specs = specs.filter(needles_per_inch=Decimal(gauge))
                except InvalidOperation:
                    specs = specs.none()
            return success_response(
                WeavingMachineSpecSerializer(specs, many=True).data,
                "Machine specs retrieved successfully!",
            )
        require_design(request.user)
        return _saved(
            SpecWriteSerializer(data=request.data, context={"machine": machine}),
            read_with=WeavingMachineSpecSerializer,
            message="Machine spec created successfully!",
            created=True,
        )

    @extend_schema(methods=["GET"], **list_bars_document)
    @extend_schema(methods=["POST"], **create_bar_document)
    @action(detail=True, methods=["get", "post"], url_path="bars")
    def bars(self, request, pk=None):
        machine = get_instance(WeavingMachine, pk)
        if request.method == "GET":
            return success_response(
                WeavingMachineBarSerializer(machine.bars.all(), many=True).data,
                "Bars retrieved successfully!",
            )
        require_design(request.user)
        return _saved(
            BarWriteSerializer(data=request.data, context={"machine": machine}),
            read_with=WeavingMachineBarSerializer,
            message="Bar created successfully!",
            created=True,
        )


class WeavingMachineSpecViewSet(viewsets.ViewSet):
    @extend_schema(**get_spec_document)
    def retrieve(self, request, pk=None):
        spec = get_instance(WeavingMachineSpec, pk)
        return success_response(
            WeavingMachineSpecSerializer(spec).data,
            "Machine spec retrieved successfully!",
        )

    @extend_schema(**update_spec_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
        spec = get_instance(WeavingMachineSpec, pk)
        return _saved(
            SpecUpdateSerializer(spec, data=request.data, partial=True),
            read_with=WeavingMachineSpecSerializer,
            message="Machine spec updated successfully!",
        )

    @extend_schema(**delete_spec_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        spec = get_instance(WeavingMachineSpec, pk)
        delete_spec(spec)
        return success_response(None, "Machine spec deleted successfully!")


class WeavingMachineBarViewSet(viewsets.ViewSet):
    @extend_schema(**get_bar_document)
    def retrieve(self, request, pk=None):
        bar = get_instance(WeavingMachineBar, pk)
        return success_response(
            WeavingMachineBarSerializer(bar).data,
            "Bar retrieved successfully!",
        )

    @extend_schema(**update_bar_document)
    def partial_update(self, request, pk=None):
        require_design(request.user)
        bar = get_instance(WeavingMachineBar, pk)
        return _saved(
            BarUpdateSerializer(bar, data=request.data, partial=True),
            read_with=WeavingMachineBarSerializer,
            message="Bar updated successfully!",
        )

    @extend_schema(**delete_bar_document)
    def destroy(self, request, pk=None):
        require_design(request.user)
        bar = get_instance(WeavingMachineBar, pk)
        delete_bar(bar)
        return success_response(None, "Bar deleted successfully!")
