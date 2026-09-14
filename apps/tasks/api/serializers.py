from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.tasks.models import Label, Task


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ["id", "project", "name", "color"]


class TaskSerializer(serializers.ModelSerializer):
    assignees = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    labels = serializers.PrimaryKeyRelatedField(many=True, queryset=Label.objects.all(), required=False)
    # Kept alongside the plain id fields above (used by write paths like
    # the assign action) rather than replacing them — the frontend needs
    # a name to render, but nothing should have to guess whether "assignees"
    # is ids or objects depending on which endpoint returned it.
    assignees_detail = UserSerializer(source="assignees", many=True, read_only=True)
    created_by_detail = UserSerializer(source="created_by", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "created_by",
            "created_by_detail",
            "priority",
            "workflow_state",
            "due_date",
            "estimated_hours",
            "labels",
            "assignees",
            "assignees_detail",
            "created_at",
            "updated_at",
        ]
        # workflow_state is only ever changed through the transition action
        # (WorkflowService enforces the state machine there); a plain PATCH
        # must not be able to set it directly.
        read_only_fields = ["id", "created_by", "workflow_state", "created_at", "updated_at"]

    def validate_labels(self, value):
        # TaskService.add_label() only runs on the create path
        # (TaskViewSet.perform_create); ModelViewSet's default update()
        # calls serializer.save() directly, so without this check a plain
        # PATCH could attach another project's label to a task with no
        # validation at all.
        project_id = self.instance.project_id if self.instance is not None else self.initial_data.get("project")
        if project_id is not None:
            project_id = int(project_id)
            for label in value:
                if label.project_id != project_id:
                    raise serializers.ValidationError(
                        f"Label '{label.name}' belongs to a different project than this task."
                    )
        return value

    def validate(self, attrs):
        # "project" must stay writable for creation (a task has to be
        # created inside some project) but is not read-only overall, so
        # this is enforced here instead of via read_only_fields: an update
        # must not be able to move a task into a different project the
        # caller was never checked as a member of for this task.
        if self.instance is not None and "project" in attrs and attrs["project"] != self.instance.project:
            raise serializers.ValidationError({"project": "A task's project cannot be changed after creation."})
        return attrs


class TaskAssignSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class TaskTransitionSerializer(serializers.Serializer):
    to_state_id = serializers.IntegerField()
