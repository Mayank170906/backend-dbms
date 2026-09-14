from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.organizations.models import Organization


class Workflow(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="workflows")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_workflow_name_per_organization"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization})"


class WorkflowState(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="states")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    order = models.PositiveIntegerField()
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["workflow", "slug"], name="unique_state_slug_per_workflow"),
            models.UniqueConstraint(fields=["workflow", "order"], name="unique_state_order_per_workflow"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.workflow})"


class WorkflowTransition(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name="outgoing_transitions")
    to_state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name="incoming_transitions")
    # Postgres ArrayField instead of a related model/M2M: the roles allowed
    # to perform a transition are a small, unordered set of strings with no
    # attributes of their own — a separate table would just be overhead a
    # native array column doesn't need. Values are validated against
    # ProjectMembership.Role in WorkflowService, not via model `choices`
    # (which Postgres wouldn't enforce anyway), to avoid an import cycle
    # between the workflows and projects apps.
    allowed_roles = ArrayField(models.CharField(max_length=20), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Also serves as the index WorkflowService needs to look up "is
            # there a transition from this state to that one" — no separate
            # index required.
            models.UniqueConstraint(
                fields=["workflow", "from_state", "to_state"], name="unique_transition_per_workflow"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state} ({self.workflow})"
