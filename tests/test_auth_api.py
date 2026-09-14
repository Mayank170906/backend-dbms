import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_register_hashes_password_and_never_returns_it(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"username": "alice", "email": "alice@example.com", "password": "S3curePass!23"},
        format="json",
    )
    assert response.status_code == 201
    assert "password" not in response.data

    user = User.objects.get(username="alice")
    assert user.password != "S3curePass!23"
    assert user.check_password("S3curePass!23")


def test_login_returns_access_and_refresh_tokens(api_client):
    api_client.post(
        "/api/v1/auth/register/",
        {"username": "bob", "email": "bob@example.com", "password": "S3curePass!23"},
        format="json",
    )
    response = api_client.post("/api/v1/auth/login/", {"username": "bob", "password": "S3curePass!23"}, format="json")
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


def test_login_with_wrong_password_rejected(api_client):
    api_client.post(
        "/api/v1/auth/register/",
        {"username": "carol", "email": "carol@example.com", "password": "S3curePass!23"},
        format="json",
    )
    response = api_client.post("/api/v1/auth/login/", {"username": "carol", "password": "wrong"}, format="json")
    assert response.status_code == 401


def test_logout_blacklists_the_refresh_token(api_client):
    api_client.post(
        "/api/v1/auth/register/",
        {"username": "dave", "email": "dave@example.com", "password": "S3curePass!23"},
        format="json",
    )
    login = api_client.post("/api/v1/auth/login/", {"username": "dave", "password": "S3curePass!23"}, format="json")
    access, refresh = login.data["access"], login.data["refresh"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_response = client.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
    assert logout_response.status_code == 204

    refresh_response = APIClient().post("/api/v1/auth/login/refresh/", {"refresh": refresh}, format="json")
    assert refresh_response.status_code == 401


def test_unauthenticated_request_is_rejected(api_client):
    response = api_client.get("/api/v1/organizations/")
    assert response.status_code == 401


def test_password_reset_request_does_not_reveal_whether_email_exists(api_client):
    # Same 200 whether or not the email matches an account — a differing
    # response would let a caller enumerate registered addresses.
    known = api_client.post(
        "/api/v1/auth/register/",
        {"username": "erin", "email": "erin@example.com", "password": "S3curePass!23"},
        format="json",
    )
    assert known.status_code == 201

    response_known = api_client.post("/api/v1/auth/password-reset/", {"email": "erin@example.com"}, format="json")
    response_unknown = api_client.post(
        "/api/v1/auth/password-reset/", {"email": "nobody-here@example.com"}, format="json"
    )
    assert response_known.status_code == response_unknown.status_code == 200
