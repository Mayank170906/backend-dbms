// Hand-maintained search index for the Ctrl+K palette (main.js). One entry
// per page; `keywords` should include real model/class/endpoint/env-var
// names so a reader can jump straight to the page that defines something
// they saw in the code. No build step generates this — it's kept in sync
// by hand alongside nav-data.js whenever a page is added.
const SEARCH_INDEX = [
  // ---- Overview ----
  { title: "Hub", section: "Overview", url: "index.html", keywords: ["home", "hub", "documentation map"], summary: "Homepage: status, stack, architecture preview, documentation map." },
  { title: "Project Overview", section: "Overview", url: "overview/project-overview.html", keywords: ["what is backend dbms", "multi-tenant", "jira", "linear", "trello"], summary: "What Backend DBMS is and why it exists." },
  { title: "Features", section: "Overview", url: "overview/features.html", keywords: ["organizations", "teams", "workflows", "tasks", "comments", "mentions", "notifications", "search", "real-time"], summary: "Feature list grouped by Django app." },
  { title: "Current Status", section: "Overview", url: "overview/current-status.html", keywords: ["implemented", "configured", "not implemented", "redis", "celery", "channels", "ci"], summary: "What's implemented vs. configured-but-not-provisioned." },
  { title: "Technology Stack", section: "Overview", url: "overview/technology-stack.html", keywords: ["django", "drf", "postgresql", "redis", "celery", "channels", "daphne", "whitenoise", "docker", "uv", "psycopg", "pillow"], summary: "Every real dependency, why it's used, and where." },
  { title: "System Overview", section: "Overview", url: "overview/system-overview.html", keywords: ["architecture diagram", "components"], summary: "The system in one picture." },

  // ---- Getting Started ----
  { title: "Prerequisites", section: "Getting Started", url: "getting-started/prerequisites.html", keywords: ["python 3.12", "uv", "docker", "postgresql 16", "redis 7"], summary: "What you need installed before running the project." },
  { title: "Installation", section: "Getting Started", url: "getting-started/installation.html", keywords: ["uv sync", "git clone", "pyproject.toml", "uv.lock"], summary: "Cloning and installing dependencies with uv." },
  { title: "Environment Setup", section: "Getting Started", url: "getting-started/environment-setup.html", keywords: [".env", ".env.example", "DJANGO_SETTINGS_MODULE", "DEBUG", "SECRET_KEY"], summary: "Configuring .env for local development." },
  { title: "Database Setup", section: "Getting Started", url: "getting-started/database-setup.html", keywords: ["migrate", "seed_data", "postgres", "DATABASE_URL"], summary: "Migrating and seeding a local database." },
  { title: "Running Locally", section: "Getting Started", url: "getting-started/running-locally.html", keywords: ["runserver", "celery worker", "celery beat"], summary: "Running the dev server without Docker." },
  { title: "Running with Docker", section: "Getting Started", url: "getting-started/running-with-docker.html", keywords: ["docker compose up", "docker-compose.yml", "db", "redis", "web", "worker", "beat"], summary: "The full stack via docker compose up." },
  { title: "First Request", section: "Getting Started", url: "getting-started/first-request.html", keywords: ["register", "login", "curl", "websocket", "access token"], summary: "Register, log in, and call the API." },

  // ---- Architecture ----
  { title: "System Architecture", section: "Architecture", url: "architecture/system-architecture.html", keywords: ["deployment topology", "multi-tenancy", "organization", "ownership chain"], summary: "Deployment topology and the multi-tenancy model." },
  { title: "High-Level Design", section: "Architecture", url: "architecture/hld.html", keywords: ["hld", "components", "asgi"], summary: "The system's major components and how they connect." },
  { title: "Low-Level Design", section: "Architecture", url: "architecture/lld.html", keywords: ["lld", "app layout", "dependency direction", "cache-aside"], summary: "App-by-app layout and dependency direction." },
  { title: "Components", section: "Architecture", url: "architecture/components.html", keywords: ["api_router.py", "routing.py", "channels_auth.py", "exceptions.py", "celery.py", "asgi.py"], summary: "The config/ support modules and their roles." },
  { title: "Data Flow", section: "Architecture", url: "architecture/data-flow.html", keywords: ["task creation", "validation", "serializer", "service", "orm"], summary: "How a write moves from request body to database row." },
  { title: "Request Lifecycle", section: "Architecture", url: "architecture/request-lifecycle.html", keywords: ["middleware", "url resolver", "jwt authentication", "permission", "viewset", "step diagram"], summary: "Twelve stages, client to Postgres — step-through diagram." },
  { title: "Authentication Flow", section: "Architecture", url: "architecture/authentication-flow.html", keywords: ["register", "login", "refresh", "logout", "jwt", "simple_jwt", "step diagram"], summary: "The JWT lifecycle — step-through diagram." },
  { title: "Deployment Architecture", section: "Architecture", url: "architecture/deployment-architecture.html", keywords: ["render", "supabase", "github", "docker"], summary: "GitHub, Render, and Supabase's roles." },
  { title: "OOP / Class Design", section: "Architecture", url: "architecture/oop-class-design.html", keywords: ["inheritance", "encapsulation", "polymorphism", "abstraction", "composition", "AbstractUser", "GenericForeignKey"], summary: "OOP concepts shown with real project classes." },

  // ---- Codebase ----
  { title: "Project Structure", section: "Codebase", url: "codebase/project-structure.html", keywords: ["apps/", "config/", "tests/", "docker/", "templates/", "static", "media"], summary: "The annotated repository tree." },
  { title: "Applications", section: "Codebase", url: "codebase/applications.html", keywords: ["accounts", "organizations", "workflows", "projects", "tasks", "comments", "activity", "notifications", "analytics"], summary: "The 9 Django apps, one paragraph each." },
  { title: "Models", section: "Codebase", url: "codebase/models.html", keywords: ["User", "Organization", "Membership", "Team", "Project", "ProjectMembership", "ProjectExport", "Workflow", "WorkflowState", "WorkflowTransition", "Task", "Label", "TaskAssignment", "Comment", "ActivityLog", "Notification"], summary: "Every model, field, and constraint." },
  { title: "Views", section: "Codebase", url: "codebase/views.html", keywords: ["RegisterView", "LoginView", "TaskViewSet", "ProjectViewSet", "OrganizationViewSet", "SearchView", "ViewSet"], summary: "Every view/viewset class and its custom actions." },
  { title: "Serializers", section: "Codebase", url: "codebase/serializers.html", keywords: ["TaskSerializer", "RegisterSerializer", "ProjectExportSerializer", "validate_labels"], summary: "Every serializer, its fields, and validation." },
  { title: "URLs", section: "Codebase", url: "codebase/urls.html", keywords: ["api_router.py", "api/v1", "routing", "endpoints"], summary: "The complete URL map." },
  { title: "Services", section: "Codebase", url: "codebase/services.html", keywords: ["OrganizationService", "TaskService", "CommentService", "ProjectService", "WorkflowService", "ActivityService", "NotificationService"], summary: "Every service class and method." },
  { title: "Permissions", section: "Codebase", url: "codebase/permissions.html", keywords: ["IsOrganizationAdmin", "IsProjectManager", "object-level permission"], summary: "The two real DRF permission classes." },
  { title: "Middleware", section: "Codebase", url: "codebase/middleware.html", keywords: ["MIDDLEWARE", "JWTAuthMiddleware", "no custom middleware"], summary: "No custom middleware exists — here's the real stack." },
  { title: "Utilities", section: "Codebase", url: "codebase/utilities.html", keywords: ["env_bool", "env_list", "cache key"], summary: "The small, real helper functions." },
  { title: "Signals", section: "Codebase", url: "codebase/signals.html", keywords: ["post_save", "post_delete", "ready()", "search vector"], summary: "Every signal receiver and its app hook." },
  { title: "Configuration", section: "Codebase", url: "codebase/configuration.html", keywords: ["base.py", "development.py", "production.py", "SECRET_KEY", "DATABASE_URL", "SIMPLE_JWT"], summary: "How the settings package fits together." },

  // ---- API ----
  { title: "API Overview", section: "API", url: "api/overview.html", keywords: ["/api/v1/", "pagination", "throttling", "drf-spectacular", "schema"], summary: "Base path, pagination, filtering, throttling, schema." },
  { title: "Authentication", section: "API", url: "api/authentication.html", keywords: ["Bearer token", "JWT", "login", "refresh", "logout"], summary: "JWT bearer tokens for HTTP, query-string token for WebSocket." },
  { title: "Endpoints", section: "API", url: "api/endpoints.html", keywords: ["organizations", "projects", "tasks", "labels", "workflows", "notifications", "search", "route table"], summary: "Every real route in the API." },
  { title: "Request/Response Examples", section: "API", url: "api/request-response-examples.html", keywords: ["create task", "transition", "export", "json example"], summary: "Realistic request/response JSON." },
  { title: "Error Handling", section: "API", url: "api/error-handling.html", keywords: ["custom_exception_handler", "404 vs 403", "error envelope"], summary: "The error envelope and 404-vs-403 pattern." },
  { title: "API Architecture", section: "API", url: "api/architecture.html", keywords: ["REST_FRAMEWORK", "DEFAULT_AUTHENTICATION_CLASSES", "DEFAULT_PERMISSION_CLASSES"], summary: "How auth/permissions/filtering/pagination fit together." },

  // ---- Database ----
  { title: "Database Overview", section: "Database", url: "database/overview.html", keywords: ["postgresql", "supabase", "DATABASE_URL", "full-text search", "ArrayField"], summary: "Why Postgres, and how it's reached." },
  { title: "ER Diagram", section: "Database", url: "database/er-diagram.html", keywords: ["entity relationship", "schema diagram", "foreign keys"], summary: "All 17 real models and their relationships." },
  { title: "Models", section: "Database", url: "database/models.html", keywords: ["business purpose", "table purpose"], summary: "Business purpose per model." },
  { title: "Relationships", section: "Database", url: "database/relationships.html", keywords: ["PROTECT", "CASCADE", "SET_NULL", "GenericForeignKey", "on_delete"], summary: "Why PROTECT/CASCADE/SET_NULL are used where they are." },
  { title: "Constraints", section: "Database", url: "database/constraints.html", keywords: ["UniqueConstraint", "RegexValidator", "unique_together"], summary: "Every real UniqueConstraint and validator." },
  { title: "Indexes", section: "Database", url: "database/indexes.html", keywords: ["Index", "GinIndex", "search_vector"], summary: "Every real index, tied to the query it serves." },
  { title: "Migrations", section: "Database", url: "database/migrations.html", keywords: ["makemigrations", "migrate", "unapplied migrations"], summary: "How schema changes are generated and applied." },

  // ---- Requirements ----
  { title: "SRS", section: "Requirements", url: "requirements/srs.html", keywords: ["software requirements specification", "IEEE-830", "scope", "product perspective"], summary: "Formal IEEE-830-style requirements document." },
  { title: "Functional Requirements", section: "Requirements", url: "requirements/functional-requirements.html", keywords: ["FR-001", "functional requirements"], summary: "FR-001 through FR-010, mapped to real code." },
  { title: "Non-Functional Requirements", section: "Requirements", url: "requirements/non-functional-requirements.html", keywords: ["NFR-001", "security", "performance", "reliability"], summary: "NFR-001 through NFR-006, with evidence." },
  { title: "Actors", section: "Requirements", url: "requirements/actors.html", keywords: ["OWNER", "ADMIN", "MEMBER", "VIEWER", "MANAGER", "DEVELOPER", "roles"], summary: "Every user class and role." },
  { title: "Use Cases", section: "Requirements", url: "requirements/use-cases.html", keywords: ["UC-01", "use case", "main flow"], summary: "Major use cases mapped to real service methods." },
  { title: "Traceability Matrix", section: "Requirements", url: "requirements/traceability-matrix.html", keywords: ["requirement to code", "test mapping"], summary: "Requirement → module → file → class → test." },

  // ---- Workflows ----
  { title: "User Workflows", section: "Workflows", url: "workflows/user-workflows.html", keywords: ["onboarding", "organization setup", "project setup", "working with tasks"], summary: "What a real user does, end to end." },
  { title: "Authentication Workflow", section: "Workflows", url: "workflows/authentication-workflow.html", keywords: ["login", "refresh", "logout", "user journey"], summary: "The JWT lifecycle as a user journey." },
  { title: "API Request Workflow", section: "Workflows", url: "workflows/api-request-workflow.html", keywords: ["step diagram", "transaction", "on_commit"], summary: "Client action to notification broadcast — step-through diagram." },
  { title: "Major Business Workflows", section: "Workflows", url: "workflows/major-business-workflows.html", keywords: ["task lifecycle", "create assign transition export"], summary: "The task lifecycle end to end." },
  { title: "Sequence Diagrams", section: "Workflows", url: "workflows/sequence-diagrams.html", keywords: ["synchronous", "asynchronous", "celery job", "websocket broadcast"], summary: "Sync API call, async job, real-time broadcast." },

  // ---- Testing ----
  { title: "Test Architecture", section: "Testing", url: "testing/architecture.html", keywords: ["pytest", "pytest-django", "pytest-asyncio", "reuse-db"], summary: "pytest setup, all tests centralized under tests/." },
  { title: "Test Cases", section: "Testing", url: "testing/test-cases.html", keywords: ["test_auth_api", "test_tasks_api", "test_security_idor", "test_transactions"], summary: "All 17 test files and what each verifies." },
  { title: "Running Tests", section: "Testing", url: "testing/running-tests.html", keywords: ["uv run pytest", "--cov=apps", "--create-db"], summary: "The exact commands to run the suite." },
  { title: "Coverage", section: "Testing", url: "testing/coverage.html", keywords: ["78 tests", "90% coverage", "cov-report"], summary: "What the reported coverage figure covers." },

  // ---- Deployment ----
  { title: "Local", section: "Deployment", url: "deployment/local.html", keywords: ["native postgres", "no docker"], summary: "Running without Docker." },
  { title: "Docker", section: "Deployment", url: "deployment/docker.html", keywords: ["Dockerfile", "docker-compose.yml", "docker-compose.prod.yml", "entrypoint.sh", "uv sync --frozen"], summary: "The Dockerfile and dev-vs-prod compose differences." },
  { title: "Render", section: "Deployment", url: "deployment/render.html", keywords: ["backend-dbms-p4su.onrender.com", "ALLOWED_HOSTS", "$PORT", "daphne"], summary: "How this project is actually deployed in production." },
  { title: "Supabase", section: "Deployment", url: "deployment/supabase.html", keywords: ["session pooler", "SUPABASE_URL", "DATABASE_URL"], summary: "PostgreSQL's role and the Session Pooler connection." },
  { title: "Environment Variables (Deployment)", section: "Deployment", url: "deployment/environment-variables.html", keywords: ["env vars per environment"], summary: "Which variables matter in which environment." },
  { title: "Production Configuration", section: "Deployment", url: "deployment/production-configuration.html", keywords: ["HSTS", "SECURE_SSL_REDIRECT", "CSRF_TRUSTED_ORIGINS", "RuntimeError"], summary: "What production.py actually guarantees." },
  { title: "Troubleshooting", section: "Deployment", url: "deployment/troubleshooting.html", keywords: ["connection refused", "Invalid HTTP_HOST", "unapplied migrations", "redis connection refused"], summary: "Real problems, their cause, and the fix." },

  // ---- Developer Notes ----
  { title: "Django Concepts", section: "Developer Notes", url: "developer-notes/django-concepts.html", keywords: ["settings package", "AUTH_USER_MODEL", "migrations", "url resolution"], summary: "Settings, apps, models, migrations, URLs." },
  { title: "DRF Concepts", section: "Developer Notes", url: "developer-notes/drf-concepts.html", keywords: ["serializers", "viewsets", "get_queryset", "mixins"], summary: "Serializers, ViewSets, routers, permissions." },
  { title: "ORM Notes", section: "Developer Notes", url: "developer-notes/orm-notes.html", keywords: ["select_related", "prefetch_related", "on_delete", "ArrayField", "SearchVectorField"], summary: "on_delete, N+1 avoidance, transactions." },
  { title: "Authentication Notes", section: "Developer Notes", url: "developer-notes/authentication-notes.html", keywords: ["access token", "refresh token", "rotation", "blacklist"], summary: "Access vs. refresh tokens and WS auth." },
  { title: "Deployment Notes", section: "Developer Notes", url: "developer-notes/deployment-notes.html", keywords: ["container networking", "build-time env vars", "ASGI"], summary: "Container networking and build-vs-run env vars." },
  { title: "What Does This Code Mean?", section: "Developer Notes", url: "developer-notes/what-does-this-code-mean.html", keywords: ["transition_task", "ActivityLog save", "JWTAuthMiddleware"], summary: "Four real snippets, explained line by line." },

  // ---- Reference ----
  { title: "Environment Variables", section: "Reference", url: "reference/environment-variables.html", keywords: ["DJANGO_SETTINGS_MODULE", "SECRET_KEY", "DATABASE_URL", "REDIS_URL", "full reference table"], summary: "Every variable, purpose, required, sensitive, used-by." },
  { title: "Commands", section: "Reference", url: "reference/commands.html", keywords: ["uv sync", "manage.py", "pytest", "celery", "docker compose"], summary: "Every real, valid command for this repo." },
  { title: "Configuration", section: "Reference", url: "reference/configuration.html", keywords: ["settings index"], summary: "Index into the Codebase and Deployment configuration pages." },
  { title: "Glossary", section: "Reference", url: "reference/glossary.html", keywords: ["JWT", "IDOR", "GIN index", "N+1", "ORM", "service layer", "webSocket"], summary: "Every term used across this documentation." },
  { title: "ADRs", section: "Reference", url: "reference/adrs.html", keywords: ["architecture decision record", "ADR-001"], summary: "Meaningful architectural decisions, with context and consequences." },
  { title: "FAQ", section: "Reference", url: "reference/faq.html", keywords: ["why postgresql", "why jwt", "why service layer", "tradeoffs"], summary: "Why this choice, not the obvious alternative." },

  // ---- Legal ----
  { title: "License", section: "Legal", url: "legal/license.html", keywords: ["no license file", "copyright", "CC BY"], summary: "Source code has no LICENSE file; documentation reuse policy." },
  { title: "Terms", section: "Legal", url: "legal/terms.html", keywords: ["as-is", "no warranty"], summary: "Plain-language terms for using this documentation site." },
  { title: "Attribution", section: "Legal", url: "legal/attribution.html", keywords: ["fonts", "third-party packages", "credits"], summary: "Credits for fonts and third-party packages." },
];
