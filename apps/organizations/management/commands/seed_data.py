import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.comments.services import CommentService
from apps.organizations.models import Membership, Organization
from apps.organizations.services import OrganizationService, TeamService
from apps.projects.models import Project, ProjectMembership
from apps.projects.services import ProjectService
from apps.tasks.models import Label, Task
from apps.tasks.services import TaskService
from apps.workflows.services import WorkflowService

FIRST_NAMES = ["Alice", "Bob", "Carol", "Dave", "Erin", "Frank", "Grace", "Heidi", "Ivan", "Judy"]
LAST_NAMES = ["Nguyen", "Smith", "Patel", "Garcia", "Kim", "Rossi", "Muller", "Chen", "Silva", "Kowalski"]

ORG_NAMES = ["Demo: Acme Corp", "Demo: Globex Industries", "Demo: Initech"]
TEAM_NAMES = ["Platform", "Growth", "Mobile"]
PROJECT_NAMES = [
    "Website Redesign", "Mobile App Revamp", "API Gateway", "Billing System",
    "Customer Portal", "Internal Tools", "Data Pipeline", "Search Overhaul",
]
LABELS = [("bug", "#DC2626"), ("feature", "#2563EB"), ("urgent", "#F59E0B"), ("tech-debt", "#6B7280")]
TASK_VERBS = ["Fix", "Implement", "Investigate", "Refactor", "Add", "Remove", "Update", "Document"]
TASK_SUBJECTS = [
    "login flow", "checkout page", "notification bell", "search ranking", "CSV export",
    "workflow transitions", "rate limiting", "avatar upload", "email templates", "dashboard charts",
    "pagination bug", "cache invalidation", "activity feed", "member invites", "task filters",
]
COMMENT_BODIES = [
    "Started looking into this, will update soon.",
    "Can someone confirm this happens in staging too?",
    "Fixed in the latest commit, please review.",
    "This is blocked on the API change from last sprint.",
    "Great catch — added a regression test for this.",
]


class Command(BaseCommand):
    help = "Seeds the database with realistic demo data: organizations, users, teams, workflows, projects, tasks, comments, and (via the normal service layer) activity logs and notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete previously seeded demo organizations (and everything under them) before seeding.",
        )

    def handle(self, *args, **options):
        random.seed(42)  # reproducible demo data across runs

        if options["clear"]:
            self._clear()

        users = self._create_users()
        for org_name in ORG_NAMES:
            self._seed_organization(org_name, users)

        self.stdout.write(self.style.SUCCESS("Seed data created."))

    def _clear(self):
        orgs = Organization.objects.filter(name__in=ORG_NAMES)
        count = orgs.count()
        # Projects (and therefore Tasks) must go first: Task.workflow_state
        # is PROTECT (Phase 4 — a task's history shouldn't vanish because a
        # workflow definition changed), which blocks Organization.delete()
        # from cascading into its Workflows while any Task still points at
        # one of their states.
        Project.objects.filter(organization__in=orgs).delete()
        orgs.delete()
        self.stdout.write(f"Cleared {count} previously seeded organization(s).")

    def _create_users(self) -> list[User]:
        users = []
        for i, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES), start=1):
            username = f"{first.lower()}{last.lower()}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first,
                    "last_name": last,
                },
            )
            if created:
                user.set_password("DemoPass123!")
                user.save(update_fields=["password"])
            users.append(user)
        self.stdout.write(f"Users ready: {len(users)} (password for all: DemoPass123!)")
        return users

    def _seed_organization(self, name: str, all_users: list[User]) -> None:
        if Organization.objects.filter(name=name).exists():
            self.stdout.write(f"Skipping '{name}' — already exists (use --clear to reseed).")
            return

        owner, *rest = random.sample(all_users, k=min(6, len(all_users)))
        org = OrganizationService.create_organization(owner=owner, name=name, description=f"{name} — seeded demo data")

        for member in rest:
            OrganizationService.add_member(organization=org, user=member, role=Membership.Role.MEMBER)

        for team_name in random.sample(TEAM_NAMES, k=2):
            TeamService.create_team(organization=org, name=team_name, description=f"{team_name} team")

        workflow = WorkflowService.create_workflow(organization=org, name="Standard Dev Workflow", actor=owner)
        backlog = WorkflowService.add_state(workflow=workflow, name="Backlog", order=1, is_initial=True, actor=owner)
        todo = WorkflowService.add_state(workflow=workflow, name="Todo", order=2, actor=owner)
        in_progress = WorkflowService.add_state(workflow=workflow, name="In Progress", order=3, actor=owner)
        review = WorkflowService.add_state(workflow=workflow, name="Code Review", order=4, actor=owner)
        done = WorkflowService.add_state(workflow=workflow, name="Done", order=5, is_terminal=True, actor=owner)
        states = [backlog, todo, in_progress, review, done]
        for from_state, to_state in zip(states, states[1:]):
            roles = ["MANAGER"] if to_state is done else []
            WorkflowService.add_transition(
                workflow=workflow, from_state=from_state, to_state=to_state, allowed_roles=roles, actor=owner
            )

        members = [owner, *rest]
        for project_name in random.sample(PROJECT_NAMES, k=3):
            self._seed_project(org, owner, members, project_name, workflow, states)

        self.stdout.write(f"Seeded organization '{name}' with {len(members)} members.")

    def _seed_project(self, org, owner, members, name, workflow, states) -> None:
        project = ProjectService.create_project(
            organization=org, owner=owner, name=name, description=f"{name} for {org.name}"
        )
        project.workflow = workflow
        project.save(update_fields=["workflow"])

        project_team = random.sample(members, k=min(len(members), random.randint(3, len(members))))
        for member in project_team:
            if member == owner:
                continue
            role = random.choice([ProjectMembership.Role.DEVELOPER, ProjectMembership.Role.DEVELOPER, ProjectMembership.Role.MANAGER])
            ProjectService.add_member(project=project, user=member, role=role, actor=owner)

        labels = [
            Label.objects.create(project=project, name=label_name, color=color) for label_name, color in LABELS
        ]

        backlog, todo, in_progress, review, done = states
        today = timezone.localdate()

        for _ in range(random.randint(8, 12)):
            title = f"{random.choice(TASK_VERBS)} {random.choice(TASK_SUBJECTS)}"
            due_date = today + timedelta(days=random.randint(-5, 20)) if random.random() < 0.7 else None
            task = TaskService.create_task(
                project=project,
                created_by=random.choice(project_team),
                title=title,
                description=f"Auto-generated demo task: {title.lower()}.",
                priority=random.choice(list(Task.Priority.values)),
                due_date=due_date,
                estimated_hours=random.choice([None, 2, 4, 8, 16]),
            )

            if random.random() < 0.8:
                assignee = random.choice(project_team)
                TaskService.assign(task=task, user=assignee, actor=owner)

            if random.random() < 0.6:
                label = random.choice(labels)
                TaskService.add_label(task=task, label=label)

            # Walk the task partway through the workflow at random, always
            # respecting the same rules a real transition would (the
            # MANAGER-only final step just doesn't happen for non-manager
            # actors, exactly like it wouldn't through the API).
            path = [backlog, todo, in_progress, review, done]
            steps = random.randint(0, len(path) - 1)
            actor = owner
            for state in path[: steps + 1]:
                try:
                    WorkflowService.transition_task(task=task, to_state=state, user=actor)
                except (ValueError, PermissionError):
                    break

            for _ in range(random.randint(0, 2)):
                CommentService.add_comment(
                    task=task, author=random.choice(project_team), body=random.choice(COMMENT_BODIES)
                )
