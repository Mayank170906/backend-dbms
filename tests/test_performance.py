"""Formalizes the query-count verification done by hand in Phase 10 into
an actual regression test: the task list endpoint's query count must not
grow as the number of tasks (with assignees/labels) grows, or a future
change that removes select_related/prefetch_related would silently
reintroduce an N+1 without any test failing."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

pytestmark = pytest.mark.django_db


@pytest.fixture
def project_with_tasks(auth_client, user_factory):
    client, owner = auth_client()
    org = client.post("/api/v1/organizations/", {"name": "Acme"}, format="json").data
    project = client.post("/api/v1/projects/", {"organization": org["id"], "name": "Proj"}, format="json").data
    assignee = user_factory()
    from apps.organizations.services import OrganizationService
    from apps.projects.models import Organization, Project, ProjectMembership
    from apps.projects.services import ProjectService

    OrganizationService.add_member(organization=Organization.objects.get(pk=org["id"]), user=assignee)
    ProjectService.add_member(
        project=Project.objects.get(pk=project["id"]),
        user=assignee,
        role=ProjectMembership.Role.DEVELOPER,
        actor=owner,
    )

    def _create_tasks(count):
        for i in range(count):
            task = client.post(
                "/api/v1/tasks/", {"project": project["id"], "title": f"Task {i}"}, format="json"
            ).data
            client.post(f"/api/v1/tasks/{task['id']}/assign/", {"user_id": assignee.id}, format="json")

    return client, project, _create_tasks


def test_task_list_query_count_does_not_scale_with_row_count(project_with_tasks):
    client, project, create_tasks = project_with_tasks

    create_tasks(1)
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(f"/api/v1/tasks/?project={project['id']}")
    assert response.status_code == 200
    baseline_queries = len(ctx.captured_queries)

    create_tasks(10)
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(f"/api/v1/tasks/?project={project['id']}")
    assert response.status_code == 200
    scaled_queries = len(ctx.captured_queries)

    assert scaled_queries == baseline_queries, (
        f"query count grew from {baseline_queries} to {scaled_queries} as rows increased "
        "from 1 to 11 tasks — this is exactly the N+1 signature "
        "select_related/prefetch_related exist to prevent"
    )


def test_task_list_stays_within_a_fixed_query_budget(project_with_tasks, django_assert_max_num_queries):
    client, project, create_tasks = project_with_tasks
    create_tasks(5)
    # auth + pagination count + main query + 2 prefetches (assignees, labels)
    with django_assert_max_num_queries(6):
        client.get(f"/api/v1/tasks/?project={project['id']}")
