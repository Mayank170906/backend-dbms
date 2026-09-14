from collections import Counter

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from apps.tasks.models import Task

from .caching import PROJECT_STATISTICS_CACHE_TTL, project_statistics_cache_key
from .models import Project


def _completion_metrics(*, project: Project, tasks) -> dict:
    """Average time-to-completion and a per-day completed-tasks histogram.

    Task has no `completed_at` column — "completed" is defined entirely by
    workflow state, and a task can only be completed once it's part of a
    workflow, so this is derived from ActivityLog rather than stored
    redundantly on Task itself. Deferred from Phase 7 specifically because
    it needs the workflow engine (Phase 4) and activity log (Phase 6) both
    already in place.
    """
    from apps.activity.models import ActivityLog

    empty = {"average_completion_hours": None, "tasks_completed_per_day": {}}
    if project.workflow_id is None:
        return empty

    terminal_names = list(project.workflow.states.filter(is_terminal=True).values_list("name", flat=True))
    if not terminal_names:
        return empty

    # The first time each task's status changed *into* a terminal state —
    # not the most recent, in case a task somehow re-enters a terminal
    # state twice; "when did this first finish" is the meaningful moment.
    completion_rows = (
        ActivityLog.objects.filter(
            project=project,
            action=ActivityLog.Action.TASK_STATUS_CHANGED,
            metadata__to__in=terminal_names,
        )
        .order_by("object_id", "created_at")
        .values("object_id", "created_at")
    )
    first_completion_by_task: dict[int, object] = {}
    for row in completion_rows:
        first_completion_by_task.setdefault(row["object_id"], row["created_at"])

    if not first_completion_by_task:
        return empty

    task_created_at = dict(tasks.values_list("id", "created_at"))

    durations_seconds = []
    per_day: Counter = Counter()
    for task_id, completed_at in first_completion_by_task.items():
        created_at = task_created_at.get(task_id)
        if created_at is None:
            continue
        durations_seconds.append((completed_at - created_at).total_seconds())
        per_day[completed_at.date().isoformat()] += 1

    average_completion_hours = (
        round(sum(durations_seconds) / len(durations_seconds) / 3600, 2) if durations_seconds else None
    )
    return {
        "average_completion_hours": average_completion_hours,
        "tasks_completed_per_day": dict(per_day),
    }


def _compute_project_statistics(*, project: Project) -> dict:
    """Recomputes every number in the payload straight from Postgres.

    Runs only on a cache miss — the whole point of get_project_statistics()
    is that this function's aggregate queries don't run on every request.
    """
    tasks = Task.objects.filter(project=project)
    today = timezone.localdate()

    by_priority = dict(
        tasks.values_list("priority").annotate(count=Count("id")).values_list("priority", "count")
    )
    by_status = dict(
        tasks.filter(workflow_state__isnull=False)
        .values_list("workflow_state__name")
        .annotate(count=Count("id"))
        .values_list("workflow_state__name", "count")
    )
    completed_tasks = tasks.filter(workflow_state__is_terminal=True).count()
    overdue_tasks = (
        tasks.filter(due_date__lt=today).exclude(workflow_state__is_terminal=True).count()
    )
    workload_by_member = dict(
        tasks.exclude(assignees__isnull=True)
        .values_list("assignees__username")
        .annotate(count=Count("id"))
        .values_list("assignees__username", "count")
    )
    total_tasks = tasks.count()

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": total_tasks - completed_tasks,
        "overdue_tasks": overdue_tasks,
        "tasks_by_priority": by_priority,
        "tasks_by_status": by_status,
        "workload_by_member": workload_by_member,
        **_completion_metrics(project=project, tasks=tasks),
        "generated_at": timezone.now().isoformat(),
    }


def get_project_statistics(*, project: Project) -> dict:
    """Postgres -> compute -> Redis on a miss; Redis -> response on a hit.

    Invalidation is push-based (Django signals in apps.tasks.signals clear
    this exact key whenever a Task or TaskAssignment for this project
    changes), not TTL-only — the TTL is a safety net for any write path a
    signal doesn't cover, not the primary invalidation mechanism.
    """
    key = project_statistics_cache_key(project_id=project.id)
    cached = cache.get(key)
    if cached is not None:
        return {**cached, "cache_hit": True}
    stats = _compute_project_statistics(project=project)
    cache.set(key, stats, PROJECT_STATISTICS_CACHE_TTL)
    return {**stats, "cache_hit": False}
