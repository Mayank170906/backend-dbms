from django.core.cache import cache

# 5 minutes: long enough that a dashboard refreshing every few seconds
# doesn't repeatedly recompute aggregates over Postgres, short enough that
# stale numbers self-correct quickly even if an invalidation were ever
# missed.
PROJECT_STATISTICS_CACHE_TTL = 300


def project_statistics_cache_key(*, project_id: int) -> str:
    return f"project:{project_id}:statistics"


def invalidate_project_statistics(*, project_id: int) -> None:
    cache.delete(project_statistics_cache_key(project_id=project_id))
