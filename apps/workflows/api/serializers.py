from rest_framework import serializers

from apps.workflows.models import Workflow, WorkflowState, WorkflowTransition


class WorkflowStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowState
        fields = ["id", "workflow", "name", "slug", "order", "is_initial", "is_terminal"]
        read_only_fields = ["id", "workflow", "slug"]


class WorkflowTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTransition
        fields = ["id", "workflow", "from_state", "to_state", "allowed_roles", "created_at"]
        read_only_fields = ["id", "workflow", "created_at"]


class WorkflowSerializer(serializers.ModelSerializer):
    states = WorkflowStateSerializer(many=True, read_only=True)
    transitions = WorkflowTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = [
            "id",
            "organization",
            "name",
            "description",
            "states",
            "transitions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
