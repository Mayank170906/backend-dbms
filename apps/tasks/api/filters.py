import django_filters

from apps.tasks.models import Task


class TaskFilter(django_filters.FilterSet):
    # Friendlier alias over the FK: GET /api/v1/tasks/?status=done reads
    # naturally even though the underlying field is workflow_state (a
    # database entity, not a hardcoded status enum — see the workflows app).
    status = django_filters.CharFilter(field_name="workflow_state__slug", lookup_expr="iexact")

    class Meta:
        model = Task
        fields = ["priority", "project", "status"]
