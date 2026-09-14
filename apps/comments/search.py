from django.contrib.postgres.search import SearchVector

from .models import Comment


def update_comment_search_vector(*, comment_id: int) -> None:
    Comment.objects.filter(pk=comment_id).update(search_vector=SearchVector("body"))
