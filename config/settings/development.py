from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1")

# Convenient defaults for local/dev work only; production.py requires
# SECRET_KEY and CORS origins to be set explicitly via the environment.
if not SECRET_KEY:
    SECRET_KEY = "django-insecure-dev-only-secret-key-do-not-use-in-production"

CORS_ALLOW_ALL_ORIGINS = True
