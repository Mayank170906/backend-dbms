"""
Base Django settings shared by every environment.

Environment-specific overrides live in development.py / production.py.
Keeping the split means production never accidentally inherits a dev-only
setting (e.g. permissive ALLOWED_HOSTS) just because base.py changed.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from celery.schedules import crontab
from dotenv import load_dotenv
import os

# BASE_DIR points at the repository root (two levels up from this file:
# config/settings/base.py -> config/settings -> config -> repo root).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load variables from a .env file in the repo root, if present. In Docker,
# real environment variables (from docker-compose's env_file) take
# precedence automatically since load_dotenv() does not override existing
# environment variables by default.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("SECRET_KEY", "")

DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1")

# "daphne" must be first in INSTALLED_APPS, before django.contrib.staticfiles
# in particular: Channels' documented mechanism for making `runserver`
# ASGI/WebSocket-aware (instead of adding a second dev server process) is
# daphne overriding Django's `runserver` management command, which only
# takes effect if it's discovered ahead of staticfiles' own override.
ASGI_APPS = [
    "daphne",
]

# Apps in this project are namespaced under `apps.` and added here as they
# are built out (accounts, organizations, projects, tasks, ... in later
# phases). Third-party apps are registered now since they only need to be
# importable/configured, not exercised, for Phase 1.
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "channels",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.organizations",
    "apps.workflows",
    "apps.projects",
    "apps.tasks",
    "apps.comments",
    "apps.activity",
    "apps.notifications",
    "apps.analytics",
    # sprints added in a later phase.
]

INSTALLED_APPS = ASGI_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
#
# DATABASE_URL is parsed by dj-database-url instead of hand-rolling a NAME/
# USER/HOST/PORT block: it keeps one connection string as the single source
# of truth (matches how most PaaS/hosting providers inject Postgres creds)
# and avoids five separate env vars that have to stay in sync. psycopg 3
# ("psycopg[binary]" in pyproject.toml) is Django's supported driver for
# `django.db.backends.postgresql` from Django 4.2 onward.
# ---------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    # Defining STORAGES at all replaces Django's default dict wholesale
    # (not merges with it) — omitting "default" here silently breaks every
    # FileField/ImageField in the project (avatar uploads, project export
    # CSVs) with a StorageHandler KeyError the moment something tries to
    # save a file, since there is no longer a "default" alias to resolve.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Redis / Celery
#
# Configured here (rather than left until Phase 8) because config/celery.py
# needs somewhere to read broker/result-backend URLs from; no tasks are
# registered yet, so this has no runtime effect until later phases.
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Schedule lives in code (Celery's default file-based PersistentScheduler)
# rather than django-celery-beat's DB-backed schedule — nothing here needs
# to be editable at runtime without a deploy, and adding a package (plus
# its own migrations) just to get admin-editable crontabs isn't justified
# yet for three fixed jobs.
CELERY_BEAT_SCHEDULE = {
    "notify-tasks-due-tomorrow": {
        "task": "apps.tasks.tasks.notify_tasks_due_tomorrow",
        "schedule": crontab(hour=6, minute=0),
    },
    "generate-daily-project-reports": {
        "task": "apps.projects.tasks.generate_daily_project_reports",
        "schedule": crontab(hour=7, minute=0),
    },
    "cleanup-expired-tokens": {
        "task": "apps.accounts.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=3, minute=0),
    },
}

# Separate Redis DB index from the Celery broker (0) and result backend (1)
# — cache keys and Celery's own bookkeeping keys have no reason to share a
# keyspace, and FLUSHDB-ing one during development shouldn't risk the other.
CACHE_URL = os.environ.get("CACHE_URL", "redis://localhost:6379/2")

CACHES = {
    "default": {
        # Django's built-in Redis cache backend (4.0+, wraps redis-py,
        # already a project dependency) — no need for django-redis just to
        # get a Redis-backed cache.
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_URL,
        "TIMEOUT": 300,
    }
}

# Fourth, separate Redis DB index — the channel layer is yet another
# distinct keyspace (ephemeral pub/sub group membership) with no reason to
# share a DB with the cache, Celery broker, or Celery results.
CHANNELS_REDIS_URL = os.environ.get("CHANNELS_REDIS_URL", "redis://localhost:6379/3")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CHANNELS_REDIS_URL],
        },
    },
}

# ---------------------------------------------------------------------------
# CORS (locked down; opened up per-origin in later phases as the frontend
# needs it)
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Every endpoint requires auth unless a view explicitly opts out
    # (register/login) — safer default than opting individual views into
    # protection and forgetting one.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/day",
        "anon": "100/day",
        # Tighter, separate scope for register/login so the general anon
        # rate (shared with read-only browsing) doesn't have to be tight
        # enough to also stop credential-stuffing on its own.
        "auth": "20/hour",
    },
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Rotation + blacklist means a leaked refresh token stops working the
    # moment it's next used by its legitimate owner, instead of staying
    # valid for its full lifetime.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Backend DBMS API",
    "DESCRIPTION": "Multi-tenant workflow & project management platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
