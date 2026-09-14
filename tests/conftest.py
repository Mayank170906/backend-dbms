import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture(autouse=True)
def _clear_redis_cache():
    """Postgres state rolls back per-test (pytest-django wraps each test in
    a transaction); Redis does not. Without this, throttle counters and
    cached project statistics leak between tests and make results depend
    on execution order — this fixture makes every test start from a clean
    cache regardless of what ran before it."""
    from django.core.cache import cache

    cache.clear()
    yield


@pytest.fixture
def user_factory(db):
    counter = {"n": 0}

    def _create(**kwargs):
        counter["n"] += 1
        username = kwargs.pop("username", f"user{counter['n']}")
        email = kwargs.pop("email", f"{username}@example.com")
        password = kwargs.pop("password", "TestPass123!")
        return User.objects.create_user(username=username, email=email, password=password, **kwargs)

    return _create


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user_factory):
    """Authenticates via force_authenticate (bypasses the login endpoint)
    so tests that aren't specifically about auth aren't coupled to it —
    the auth flow itself is covered separately in test_auth_api.py."""

    def _make(user=None):
        user = user or user_factory()
        client = APIClient()
        client.force_authenticate(user=user)
        return client, user

    return _make
