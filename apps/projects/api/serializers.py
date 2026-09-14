from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.projects.models import Project, ProjectExport, ProjectMembership


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "owner",
            "status",
            "workflow",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "created_at", "updated_at"]


class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ["id", "project", "user", "role", "joined_at"]
        read_only_fields = ["id", "project", "joined_at"]


class ProjectExportSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectExport
        fields = [
            "id",
            "project",
            "requested_by",
            "status",
            "file_url",
            "error_message",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url
