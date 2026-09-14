from rest_framework import serializers

from apps.accounts.api.serializers import UserSerializer
from apps.comments.models import Comment


class CommentSerializer(serializers.ModelSerializer):
    author_detail = UserSerializer(source="author", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "author_detail", "body", "created_at", "updated_at"]
        read_only_fields = ["id", "task", "author", "created_at", "updated_at"]
