import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def org_setup(auth_client):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    return client, owner, org


def test_create_workflow_via_api(org_setup):
    client, owner, org = org_setup
    response = client.post("/api/v1/workflows/", {"organization": org["id"], "name": "WF"}, format="json")
    assert response.status_code == 201
    assert response.data["states"] == []


def test_add_state_and_transition_via_api(org_setup):
    client, owner, org = org_setup
    workflow = client.post("/api/v1/workflows/", {"organization": org["id"], "name": "WF"}, format="json").data

    backlog = client.post(
        f"/api/v1/workflows/{workflow['id']}/states/",
        {"name": "Backlog", "order": 1, "is_initial": True},
        format="json",
    ).data
    done = client.post(
        f"/api/v1/workflows/{workflow['id']}/states/",
        {"name": "Done", "order": 2, "is_terminal": True},
        format="json",
    ).data
    assert backlog["slug"] == "backlog"

    response = client.post(
        f"/api/v1/workflows/{workflow['id']}/transitions/",
        {"from_state": backlog["id"], "to_state": done["id"], "allowed_roles": ["MANAGER"]},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["allowed_roles"] == ["MANAGER"]

    workflow_detail = client.get(f"/api/v1/workflows/{workflow['id']}/").data
    assert len(workflow_detail["states"]) == 2
    assert len(workflow_detail["transitions"]) == 1


def test_transition_rejects_unknown_role(org_setup):
    client, owner, org = org_setup
    workflow = client.post("/api/v1/workflows/", {"organization": org["id"], "name": "WF"}, format="json").data
    backlog = client.post(
        f"/api/v1/workflows/{workflow['id']}/states/", {"name": "Backlog", "order": 1}, format="json"
    ).data
    done = client.post(f"/api/v1/workflows/{workflow['id']}/states/", {"name": "Done", "order": 2}, format="json").data

    response = client.post(
        f"/api/v1/workflows/{workflow['id']}/transitions/",
        {"from_state": backlog["id"], "to_state": done["id"], "allowed_roles": ["NOT_A_REAL_ROLE"]},
        format="json",
    )
    assert response.status_code == 400


def test_workflow_list_scoped_to_organization_query_param(org_setup):
    client, owner, org = org_setup
    org2 = client.post("/api/v1/organizations/", {"name": "Beta"}, format="json").data
    client.post("/api/v1/workflows/", {"organization": org["id"], "name": "WF A"}, format="json")
    client.post("/api/v1/workflows/", {"organization": org2["id"], "name": "WF B"}, format="json")

    response = client.get(f"/api/v1/workflows/?organization={org['id']}")
    names = [w["name"] for w in response.data["results"]]
    assert names == ["WF A"]


def test_non_member_cannot_author_workflow_states(auth_client, org_setup):
    client, owner, org = org_setup
    workflow = client.post("/api/v1/workflows/", {"organization": org["id"], "name": "WF"}, format="json").data

    outsider_client, _ = auth_client()
    response = outsider_client.post(
        f"/api/v1/workflows/{workflow['id']}/states/", {"name": "Backlog", "order": 1}, format="json"
    )
    assert response.status_code == 404  # workflow isn't visible to a non-member at all
