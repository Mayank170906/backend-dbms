from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Project
from .search import update_project_search_vector


@receiver(post_save, sender=Project)
def update_search_vector_on_project_save(sender, instance, **kwargs):
    update_project_search_vector(project_id=instance.pk)
