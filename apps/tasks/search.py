from django.contrib.postgres.search import SearchVector

from .models import Task


def update_task_search_vector(*, task_id: int) -> None:
    # weight="A" (title) outranks weight="B" (description) in SearchRank
    # ordering — a query matching the title is a stronger signal than one
    # only matching somewhere in a long description.
    Task.objects.filter(pk=task_id).update(
        search_vector=SearchVector("title", weight="A") + SearchVector("description", weight="B")
    )
