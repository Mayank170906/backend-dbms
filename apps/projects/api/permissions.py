from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.projects.models import ProjectMembership


class IsProjectManager(BasePermission):
    """Any project member may read; only MANAGER may write."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return ProjectMembership.objects.filter(project=obj, user=request.user).exists()
        return ProjectMembership.objects.filter(
            project=obj, user=request.user, role=ProjectMembership.Role.MANAGER
        ).exists()
