from django.contrib import admin

from .models import Project, ProjectExport, ProjectMembership


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "status", "owner", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("name", "slug", "organization__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProjectMembershipInline]


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "role", "joined_at")
    list_filter = ("role",)
    search_fields = ("user__username", "project__name")


@admin.register(ProjectExport)
class ProjectExportAdmin(admin.ModelAdmin):
    list_display = ("project", "requested_by", "status", "created_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("project__name", "requested_by__username")
    readonly_fields = ("created_at", "completed_at")
