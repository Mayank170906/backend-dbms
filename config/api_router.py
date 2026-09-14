from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import UserViewSet
from apps.analytics.api.views import SearchView
from apps.notifications.api.views import NotificationViewSet
from apps.organizations.api.views import OrganizationViewSet, TeamViewSet
from apps.projects.api.views import ProjectViewSet
from apps.tasks.api.views import LabelViewSet, TaskViewSet
from apps.workflows.api.views import WorkflowViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("teams", TeamViewSet, basename="team")
router.register("projects", ProjectViewSet, basename="project")
router.register("tasks", TaskViewSet, basename="task")
router.register("labels", LabelViewSet, basename="label")
router.register("workflows", WorkflowViewSet, basename="workflow")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("auth/", include("apps.accounts.api.urls")),
    path("search/", SearchView.as_view(), name="search"),
    path("", include(router.urls)),
]
