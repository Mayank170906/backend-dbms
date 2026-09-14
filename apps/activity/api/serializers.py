from rest_framework import serializers

from apps.activity.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    actor = serializers.SlugRelatedField(slug_field="username", read_only=True)
    object_type = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = ActivityLog
        fields = ["id", "actor", "action", "object_type", "object_id", "metadata", "created_at"]
        read_only_fields = fields
