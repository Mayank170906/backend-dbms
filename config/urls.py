from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_router")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Every page below is a dumb TemplateView with zero Django-side context —
# no view here ever touches the ORM. All data comes from client-side JS
# calling the same /api/v1/ endpoints an external API consumer would use;
# the frontend is a consumer of this project's own API, not a shortcut
# around it.
urlpatterns += [
    path("", TemplateView.as_view(template_name="dashboard.html"), name="page-dashboard"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="page-login"),
    path("register/", TemplateView.as_view(template_name="register.html"), name="page-register"),
    path(
        "organizations/<int:pk>/",
        TemplateView.as_view(template_name="organization_detail.html"),
        name="page-organization-detail",
    ),
    path(
        "projects/<int:pk>/",
        TemplateView.as_view(template_name="project_detail.html"),
        name="page-project-detail",
    ),
    path("notifications/", TemplateView.as_view(template_name="notifications.html"), name="page-notifications"),
    path("search/", TemplateView.as_view(template_name="search.html"), name="page-search"),
]

if settings.DEBUG:
    # Development convenience only: production serves MEDIA_ROOT (project
    # export CSVs, user avatars) from object storage or a real web server,
    # never through Django itself.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
