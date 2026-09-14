from django.contrib.postgres.search import SearchVector

from .models import Project


def update_project_search_vector(*, project_id: int) -> None:
    Project.objects.filter(pk=project_id).update(
        search_vector=SearchVector("name", weight="A") + SearchVector("description", weight="B")
    )
