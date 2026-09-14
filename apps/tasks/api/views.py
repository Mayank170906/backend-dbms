from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.comments.api.serializers import CommentSerializer
from apps.comments.services import CommentService
from apps.projects.models import ProjectMembership
from apps.tasks.models import Label, Task
from apps.tasks.services import TaskService
from apps.workflows.models import WorkflowState
from apps.workflows.services import WorkflowService

from .filters import TaskFilter
from .serializers import LabelSerializer, TaskAssignSerializer, TaskSerializer, TaskTransitionSerializer

User = get_user_model()


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = TaskFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date", "priority"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Task.objects.none()
        # select_related/prefetch_related here is what keeps list/detail
        # views from N+1-ing on project, creator, state, assignees, labels.
        return (
            Task.objects.filter(project__memberships__user=self.request.user)
            .select_related("project", "created_by", "workflow_state")
            .prefetch_related("assignees", "labels")
            .distinct()
        )

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        labels = serializer.validated_data.pop("labels", [])
        try:
            task = TaskService.create_task(
                project=project,
                created_by=self.request.user,
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                priority=serializer.validated_data.get("priority", Task.Priority.MEDIUM),
                due_date=serializer.validated_data.get("due_date"),
                estimated_hours=serializer.validated_data.get("estimated_hours"),
            )
        except ValueError as exc:
            raise PermissionDenied(str(exc))
        for label in labels:
            try:
                TaskService.add_label(task=task, label=label)
            except ValueError as exc:
                raise ValidationError(str(exc))
        serializer.instance = task

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        task = self.get_object()
        serializer = TaskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, pk=serializer.validated_data["user_id"])
        try:
            TaskService.assign(task=task, user=user, actor=request.user)
        except ValueError as exc:
            raise PermissionDenied(str(exc))
        # get_object()'s queryset prefetch_related("assignees") already
        # cached the (pre-assignment) empty set on this instance;
        # refresh_from_db() clears that cache so the response reflects the
        # assignment that was just written, not the stale prefetch.
        task.refresh_from_db()
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        task = self.get_object()
        serializer = TaskTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        to_state = get_object_or_404(WorkflowState, pk=serializer.validated_data["to_state_id"])
        try:
            WorkflowService.transition_task(task=task, to_state=to_state, user=request.user)
        except ValueError as exc:
            raise ValidationError(str(exc))
        except PermissionError as exc:
            raise PermissionDenied(str(exc))
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        task = self.get_object()
        if request.method == "POST":
            try:
                comment = CommentService.add_comment(
                    task=task, author=request.user, body=request.data.get("body", "")
                )
            except ValueError as exc:
                raise PermissionDenied(str(exc))
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        queryset = task.comments.select_related("author").all()
        return Response(CommentSerializer(queryset, many=True).data)


class LabelViewSet(viewsets.ModelViewSet):
    serializer_class = LabelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["project"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Label.objects.none()
        return Label.objects.filter(project__memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        if not ProjectMembership.objects.filter(project=project, user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this project.")
        serializer.save()
