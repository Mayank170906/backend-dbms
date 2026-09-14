from django.contrib import admin

from .models import Workflow, WorkflowState, WorkflowTransition


class WorkflowStateInline(admin.TabularInline):
    model = WorkflowState
    extra = 0


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_at")
    search_fields = ("name", "organization__name")
    inlines = [WorkflowStateInline]


@admin.register(WorkflowState)
class WorkflowStateAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow", "order", "is_initial", "is_terminal")
    list_filter = ("workflow", "is_initial", "is_terminal")
    search_fields = ("name", "workflow__name")


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ("workflow", "from_state", "to_state", "allowed_roles")
    list_filter = ("workflow",)
