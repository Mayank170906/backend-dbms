from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.organizations.models import Membership
from apps.workflows.models import Workflow, WorkflowState
from apps.workflows.services import WorkflowService

from .serializers import WorkflowSerializer, WorkflowStateSerializer, WorkflowTransitionSerializer


class WorkflowViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["organization"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Workflow.objects.none()
        return (
            Workflow.objects.filter(organization__memberships__user=self.request.user)
            .prefetch_related("states", "transitions")
            .distinct()
        )

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        if not Membership.objects.filter(organization=organization, user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this organization.")
        workflow = WorkflowService.create_workflow(
            organization=organization,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            actor=self.request.user,
        )
        serializer.instance = workflow

    @action(detail=True, methods=["post"], url_path="states")
    def add_state(self, request, pk=None):
        workflow = self.get_object()
        serializer = WorkflowStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = WorkflowService.add_state(
            workflow=workflow,
            name=serializer.validated_data["name"],
            order=serializer.validated_data["order"],
            is_initial=serializer.validated_data.get("is_initial", False),
            is_terminal=serializer.validated_data.get("is_terminal", False),
            actor=request.user,
        )
        return Response(WorkflowStateSerializer(state).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="transitions")
    def add_transition(self, request, pk=None):
        workflow = self.get_object()
        from_state = get_object_or_404(WorkflowState, pk=request.data.get("from_state"), workflow=workflow)
        to_state = get_object_or_404(WorkflowState, pk=request.data.get("to_state"), workflow=workflow)
        try:
            transition = WorkflowService.add_transition(
                workflow=workflow,
                from_state=from_state,
                to_state=to_state,
                allowed_roles=request.data.get("allowed_roles", []),
                actor=request.user,
            )
        except ValueError as exc:
            raise ValidationError(str(exc))
        return Response(WorkflowTransitionSerializer(transition).data, status=status.HTTP_201_CREATED)
