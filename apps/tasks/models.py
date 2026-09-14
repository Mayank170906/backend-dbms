from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import RegexValidator
from django.db import models

from apps.projects.models import Project

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Color must be a 6-digit hex code, e.g. #6B7280.",
)


class Label(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=100)
    # Validated strictly (not just length-limited): the frontend interpolates
    # this value directly into an HTML style attribute
    # (project_detail.js's label picker) without escaping it — an
    # unvalidated color string would be a stored-XSS vector via a crafted
    # value like `red" onmouseover="...`. Enforcing the format here is the
    # actual fix; the frontend also validates as defense in depth.
    color = models.CharField(max_length=7, default="#6B7280", validators=[hex_color_validator])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="unique_label_name_per_project"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project})"


class Task(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # SET_NULL (not PROTECT like Project.owner): a task is a high-cardinality
    # child record, and blocking user deletion because they once authored a
    # task would be impractical. The task itself is worth keeping even if
    # attribution is lost.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    # Workflow states are database entities (apps.workflows), never a
    # hardcoded Task.status choice field — administrators define their own
    # workflow, and the backend (WorkflowService) is the sole authority on
    # which transitions between states are valid.
    workflow_state = models.ForeignKey(
        "workflows.WorkflowState",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    labels = models.ManyToManyField(Label, blank=True, related_name="tasks")
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TaskAssignment",
        related_name="assigned_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Maintained by apps.tasks.signals on every save (kept in sync, not
    # computed at query time) so full-text search can use a GIN index
    # instead of running to_tsvector() over title+description on every row,
    # every search request.
    search_vector = SearchVectorField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "priority"]),
            models.Index(fields=["project", "due_date"]),
            models.Index(fields=["project", "workflow_state"]),
            GinIndex(fields=["search_vector"], name="task_search_vector_gin"),
        ]

    def __str__(self) -> str:
        return self.title


class TaskAssignment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "user"], name="unique_task_assignment"),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.task}"
