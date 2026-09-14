from django.contrib.postgres.search import SearchQuery, SearchRank
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comments.api.serializers import CommentSerializer
from apps.comments.models import Comment
from apps.projects.api.serializers import ProjectSerializer
from apps.projects.models import Project
from apps.tasks.api.serializers import TaskSerializer
from apps.tasks.models import Task


class SearchResultSerializer(serializers.Serializer):
    """Describes SearchView's response shape for OpenAPI schema generation
    only — the view builds the actual dict itself, since it merges three
    independent querysets rather than serializing one queryset/instance."""

    projects = ProjectSerializer(many=True)
    tasks = TaskSerializer(many=True)
    comments = CommentSerializer(many=True)


class SearchView(APIView):
    """GET /api/v1/search/?q=<query> — PostgreSQL full-text search across
    project names/descriptions, task titles/descriptions, and comment
    bodies, ranked by relevance (SearchRank) rather than plain substring
    matching.

    Every queryset is scoped to organizations/projects the caller actually
    belongs to first, same as every other endpoint — full-text search is
    still just a way to read data, not a side door around authorization.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SearchResultSerializer

    def get(self, request):
        query_text = request.query_params.get("q", "").strip()
        if not query_text:
            return Response({"projects": [], "tasks": [], "comments": []})

        search_query = SearchQuery(query_text)

        projects = (
            Project.objects.filter(organization__memberships__user=request.user, search_vector=search_query)
            .select_related("organization", "owner", "workflow")
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank")
            .distinct()[:20]
        )
        tasks = (
            Task.objects.filter(project__memberships__user=request.user, search_vector=search_query)
            .select_related("project", "created_by", "workflow_state")
            .prefetch_related("assignees", "labels")
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank")
            .distinct()[:20]
        )
        comments = (
            Comment.objects.filter(
                task__project__memberships__user=request.user, search_vector=search_query
            )
            .select_related("task", "author")
            .annotate(rank=SearchRank("search_vector", search_query))
            .order_by("-rank")
            .distinct()[:20]
        )

        return Response(
            {
                "projects": ProjectSerializer(projects, many=True).data,
                "tasks": TaskSerializer(tasks, many=True).data,
                "comments": CommentSerializer(comments, many=True).data,
            }
        )
