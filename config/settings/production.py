import os

from .base import *  # noqa: F401,F403

DEBUG = False

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable must be set in production.")

if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS environment variable must be set in production.")

if not os.environ.get("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL environment variable must be set in production.")

# Standard hardening for a service sitting behind a TLS-terminating proxy
# (nginx/load balancer). Each is individually toggleable via env vars so a
# bare-metal/non-proxied deployment isn't forced into a redirect loop.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# CSRF_COOKIE_HTTPONLY is safe here specifically because nothing in this
# project reads the csrftoken cookie from JS: the API is JWT-authenticated
# (Phase 5), and Django admin's own CSRF handling embeds the token into
# server-rendered forms rather than reading the cookie client-side.
CSRF_COOKIE_HTTPONLY = True

# Required once this sits behind a reverse proxy terminating TLS for a real
# domain — Django's CSRF check compares the Origin/Referer header against
# this list for "unsafe" (POST/PUT/PATCH/DELETE) requests, which in
# practice means the Django admin here (the API itself is CSRF-exempt by
# being JWT-authenticated, not session-authenticated).
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

CORS_ALLOW_ALL_ORIGINS = False

# The browsable API's HTML forms are a convenience for local development
# (Phase 5) with no purpose in production — every real consumer of this
# API (the frontend, an external client) sends and expects JSON. Reducing
# to JSON-only isn't fixing a vulnerability so much as shrinking the
# surface a probe has to look at.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
