import pytest

from apps.organizations.models import Membership, Organization
from apps.organizations.services import OrganizationService

pytestmark = pytest.mark.django_db


def test_creating_organization_makes_creator_the_owner(auth_client):
    client, user = auth_client()
    response = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json")
    assert response.status_code == 201

    membership = Membership.objects.get(organization_id=response.data["id"], user=user)
    assert membership.role == Membership.Role.OWNER


def test_non_member_gets_404_not_403(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    org = client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data

    response = client_b.get(f"/api/v1/organizations/{org['id']}/")
    # Not 403: a permission-denied response would confirm the org exists
    # at all, which is exactly the enumeration the IDOR requirement rules
    # out.
    assert response.status_code == 404


def test_member_list_only_shows_callers_own_organizations(auth_client):
    client_a, _ = auth_client()
    client_b, _ = auth_client()
    client_a.post("/api/v1/organizations/", {"name": "Acme"}, format="json")
    client_b.post("/api/v1/organizations/", {"name": "Beta"}, format="json")

    response_a = client_a.get("/api/v1/organizations/")
    names_a = [o["name"] for o in response_a.data["results"]]
    assert names_a == ["Acme"]


def test_viewer_role_cannot_update_organization(auth_client):
    client_owner, _ = auth_client()
    org = client_owner.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data

    client_viewer, viewer = auth_client()
    OrganizationService.add_member(
        organization=Organization.objects.get(pk=org["id"]), user=viewer, role=Membership.Role.VIEWER
    )

    response = client_viewer.patch(f"/api/v1/organizations/{org['id']}/", {"name": "Hacked"}, format="json")
    assert response.status_code == 403


def test_admin_role_can_add_members(auth_client, user_factory):
    client_owner, _ = auth_client()
    org = client_owner.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    new_member = user_factory()

    response = client_owner.post(
        f"/api/v1/organizations/{org['id']}/members/", {"user_id": new_member.id, "role": "MEMBER"}, format="json"
    )
    assert response.status_code == 201
    assert response.data["user"]["username"] == new_member.username


def test_pagination_response_shape(auth_client):
    client, _ = auth_client()
    client.post("/api/v1/organizations/", {"name": "Acme"}, format="json")
    response = client.get("/api/v1/organizations/")
    assert {"count", "next", "previous", "results"}.issubset(response.data.keys())
