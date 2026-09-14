import pytest
from django.core.management import call_command

from apps.organizations.models import Organization
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


def test_seed_data_creates_realistic_cross_model_data():
    call_command("seed_data")
    assert Organization.objects.filter(name__startswith="Demo:").count() == 3
    assert Task.objects.count() > 0


def test_seed_data_clear_actually_deletes_and_reseeds():
    call_command("seed_data")
    first_run_task_count = Task.objects.count()

    # This specifically caught a real bug: deleting Organization directly
    # hit a ProtectedError because Task.workflow_state (PROTECT) blocked
    # the cascade into Workflow while tasks still existed — Projects (and
    # their Tasks) have to be deleted first.
    call_command("seed_data", "--clear")

    assert Organization.objects.filter(name__startswith="Demo:").count() == 3
    assert Task.objects.count() == first_run_task_count  # same seed => same shape
