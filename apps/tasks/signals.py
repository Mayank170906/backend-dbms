from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.projects.caching import invalidate_project_statistics

from .models import Task, TaskAssignment
from .search import update_task_search_vector


@receiver(post_save, sender=Task)
@receiver(post_delete, sender=Task)
def invalidate_stats_on_task_change(sender, instance, **kwargs):
    invalidate_project_statistics(project_id=instance.project_id)


@receiver(post_save, sender=Task)
def update_search_vector_on_task_save(sender, instance, **kwargs):
    # .update() (not instance.save()) so this doesn't recurse back into
    # post_save — QuerySet.update() bypasses save()/signals entirely.
    update_task_search_vector(task_id=instance.pk)


@receiver(post_save, sender=TaskAssignment)
@receiver(post_delete, sender=TaskAssignment)
def invalidate_stats_on_assignment_change(sender, instance, **kwargs):
    # Workload-by-member counts derive from assignments, not the Task row
    # itself, so an assignment changing without the task changing (the
    # common case — assigning doesn't touch title/priority/etc.) still
    # needs to invalidate the same cached statistics.
    invalidate_project_statistics(project_id=instance.task.project_id)
