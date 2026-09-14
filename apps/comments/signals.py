from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Comment
from .search import update_comment_search_vector


@receiver(post_save, sender=Comment)
def update_search_vector_on_comment_save(sender, instance, **kwargs):
    update_comment_search_vector(comment_id=instance.pk)
