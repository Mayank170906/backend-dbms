import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("backend_dbms")

# Read CELERY_* settings from Django's settings module (see
# config/settings/base.py) instead of a separate celeryconfig module, so
# there is exactly one place broker/result-backend URLs are configured.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discovers a `tasks.py` in each app under apps/ once those apps exist and
# are registered in INSTALLED_APPS (Phase 8 onward). No-op today.
app.autodiscover_tasks()
