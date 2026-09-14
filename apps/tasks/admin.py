from django.contrib import admin

from .models import Label, Task, TaskAssignment


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "priority", "due_date", "created_by", "created_at")
    list_filter = ("priority", "project")
    search_fields = ("title", "description")
    filter_horizontal = ("labels",)
    inlines = [TaskAssignmentInline]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "project", "color")
    search_fields = ("name", "project__name")


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "task", "assigned_at")
    search_fields = ("user__username", "task__title")
