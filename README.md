# Backend DBMS — Multi-Tenant Workflow & Project Management Platform

A self-contained Jira/Linear/Trello-style project and workflow management
platform, built to demonstrate production-grade Django backend engineering:
REST API design, PostgreSQL/relational data modeling, authentication &
authorization, transactions, query optimization, caching, async processing,
real-time updates, and testing.

This README grows with each phase of the build; all 12 phases are now
implemented.

## Status: Complete (Phases 1–12)

Phase 12 — Testing, Security Review, Production Docker, Documentation —
closes out the build. See [Testing](#testing), [Security
Review](#security-review), [Production Deployment](#production-deployment),
and [Seed Data](#seed-data) below for what that phase specifically added;
the phase-by-phase log (Phase 11 and earlier) is preserved beneath as the
running design record of how the project got here.

## Status: Phase 11 — Frontend

What exists right now:

- Django project configured with a split-settings layout
  (`config/settings/{base,development,production}.py`)
- PostgreSQL as the database backend (via `psycopg` 3), connection
  configured from a single `DATABASE_URL` environment variable
- Redis + Celery wiring in settings (`config/celery.py`) — no tasks yet;
  this just avoids re-touching settings later
- Docker Compose for Postgres, Redis, and the Django app
- Environment-based configuration (`.env.example` → `.env`, never committed)
- `apps.accounts`: custom `User` model (`AUTH_USER_MODEL`) extending
  `AbstractUser` with a unique email, avatar, and timestamps
- `apps.organizations`: `Organization`, `Membership` (org roles:
  OWNER/ADMIN/MEMBER/VIEWER), `Team`, `TeamMembership` — plus a service
  layer (`apps/organizations/services.py`) that creates an organization and
  its owner membership atomically
- `apps.projects`: `Project` (slug unique per-organization, not globally),
  `ProjectMembership` (project roles: MANAGER/DEVELOPER/VIEWER) — service
  layer enforces that a project's owner/members must already belong to the
  project's organization
- `apps.tasks`: `Task` (priority, due date, estimated hours), `Label`,
  `TaskAssignment` (multiple assignees via a through-model) — service layer
  enforces project membership before assignment and rejects labels that
  belong to a different project than the task
- `apps.comments`: `Comment` on a `Task` — service layer enforces project
  membership before allowing a comment
- `apps.workflows`: `Workflow`, `WorkflowState`, `WorkflowTransition`
  (`allowed_roles` as a Postgres `ArrayField`) — administrators define
  arbitrary per-organization workflows (states + the transitions allowed
  between them) instead of a hardcoded task-status enum
- `Project.workflow` and `Task.workflow_state` FKs (deferred from Phase 3
  until `WorkflowState` existed as a real model) — added as their own
  migrations on top of the existing `projects`/`tasks` tables
- `WorkflowService.transition_task()` — the backend-authoritative gate for
  every state change: re-derives project membership, the current state, and
  whether a transition (and the caller's role) is permitted, straight from
  the database on every call
- Migrations applied and verified against a live PostgreSQL container,
  including end-to-end smoke tests that exercise every authorization guard
  and workflow rule (each confirmed to actually raise, not just exist in
  code)
- `/api/v1/` — a full REST surface over every model built so far, via
  `config/api_router.py`:
  - `auth/`: register, JWT login (`djangorestframework-simplejwt`), token
    refresh, logout (refresh-token blacklisting), `me/`, and a
    request/confirm password-reset flow
  - `organizations/`, `teams/`, `projects/`, `tasks/`, `labels/`,
    `workflows/` — full `ModelViewSet` CRUD, each scoped so a user only
    ever sees rows they're a member of
  - actions: `organizations/{id}/members/`, `projects/{id}/members/`
    (invite/role-assign), `tasks/{id}/assign/`, `tasks/{id}/transition/`
    (goes through `WorkflowService`, not a raw field update),
    `tasks/{id}/comments/` (list/create), `workflows/{id}/states/` and
    `workflows/{id}/transitions/` (build a workflow via the API, not just
    the admin)
  - filtering (`?priority=`, `?project=`, `?status=<state-slug>`), search
    (`?search=`), ordering (`?ordering=`), and page-number pagination on
    every list endpoint
  - a consistent `{"error": {...}}` envelope for every 4xx/5xx response
    (`config/exceptions.py`), and OpenAPI schema + Swagger UI at
    `/api/schema/` and `/api/docs/`
- Verified against a **running server**, not just `check`: a full DRF
  `APIClient` smoke test registers users, logs in, creates an org/project/
  workflow/task through the API, drives a task through a role-gated
  transition, and confirms IDOR protection, pagination shape, and
  logout/blacklist all behave — a real bug (stale `assignees` in the
  `assign` response, caused by a prefetch cache not invalidating after the
  write) was caught this way and fixed.
- `apps.activity`: `ActivityLog` — a genuinely immutable audit trail
  (`save()`/`delete()` raise on any attempted update or removal, not just
  admin-configured read-only fields) pointing at its target via a
  `GenericForeignKey`, scoped to both `organization` and (when applicable)
  `project` for efficient feed queries
- `apps.notifications`: `Notification` with `is_read`/`read_at`, surfaced at
  `GET /api/v1/notifications/`, `POST /api/v1/notifications/{id}/read/`, and
  `POST /api/v1/notifications/read-all/`
- Every existing service now logs and notifies as part of its existing
  atomic block, closing out the exact plan described (and deferred) back in
  Phase 4: `TaskService.create_task`/`assign`, `CommentService.add_comment`
  (with `@username` mention detection, notifying only mentions that resolve
  to an actual project member), `ProjectService.add_member`, and
  `WorkflowService.create_workflow`/`add_state`/`add_transition`/
  `transition_task` all write an `ActivityLog` row, and the ones with an
  affected user beyond the actor (assign, mention, transition, membership)
  also create a `Notification` — all inside the same `transaction.atomic()`
  as the underlying write, so a failure partway through rolls back the
  whole thing, not just the primary change.
- `GET /api/v1/projects/{id}/activity/` — paginated, project-scoped activity
  feed
- "Task due tomorrow" notifications (the one example from the spec that
  needs a recurring background check rather than an event hook) are
  deferred to Phase 8, once Celery Beat exists to run that check on a
  schedule.
- Verified with an end-to-end `APIClient` test that asserts on the actual
  `ActivityLog`/`Notification` rows a full org→project→workflow→task→
  assign→comment→transition flow produces — not just that the HTTP calls
  returned 2xx — including that immutability is enforced (`ActivityLog`
  update/delete both raise), that workflow-authoring events are scoped to
  the organization and not miscategorized as project events, and that the
  transition actor never receives a self-notification.
- **Redis-backed cache** (`CACHES["default"]`, Django's built-in
  `django.core.cache.backends.redis.RedisCache` — no extra dependency
  needed on top of the `redis` package already in `pyproject.toml`) on its
  own DB index (2), separate from the Celery broker (0) and result backend
  (1)
- `GET /api/v1/projects/{id}/statistics/` (`apps/projects/statistics.py`):
  total/completed/pending/overdue tasks, tasks by priority, tasks by
  workflow state, workload per member — computed from Postgres on a cache
  miss, served from Redis on a hit, with a `cache_hit` flag in the response
  so the behavior is directly observable
- **Push-based cache invalidation via Django signals**
  (`apps/tasks/signals.py`): `post_save`/`post_delete` on `Task` and
  `TaskAssignment` clear the owning project's statistics cache key
  immediately, regardless of which code path made the change (API, admin,
  shell, a future Celery task) — the cache TTL (5 minutes) is a safety net
  for anything a signal doesn't cover, not the primary invalidation
  mechanism
- As a side effect of the same `CACHES` change, DRF's rate-limit throttling
  (configured back in Phase 5) is now genuinely Redis-backed too — `SimpleRateThrottle`
  uses Django's default cache, which previously meant per-process, in-memory
  counters that don't work correctly across multiple workers
- Verified against real Redis, not just Django's cache API: wrote a key
  through `cache.set()` and confirmed it via `redis-cli` directly against
  DB 2, then ran a full miss → hit → mutate → miss cycle through the live
  API for task creation, assignment, and workflow transitions, asserting on
  the actual returned numbers (not just that invalidation "happened") —
  plus an IDOR check confirming the statistics endpoint is scoped by
  project membership like every other endpoint
- `worker` and `beat` services in `docker-compose.yml` (a shared YAML
  anchor keeps their env identical to `web`'s) — `config/celery.py`'s
  `autodiscover_tasks()` (wired up back in Phase 1) picked up every task
  below with zero additional configuration
- Password reset (`POST /api/v1/auth/password-reset/`) now queues
  `apps.accounts.tasks.send_password_reset_email` instead of calling
  `send_mail()` inline — the request no longer blocks on an email
  provider, and its response time can't leak whether sending succeeded
- `POST /api/v1/projects/{id}/export/` (`apps.projects.tasks.export_project_tasks_csv`):
  returns `202` with a `ProjectExport` row immediately; a worker generates
  the CSV, attaches it via `FileField`, and sends an `EXPORT_READY`
  notification when done (or records the error on the row if it fails —
  there's no request left to return an error response on). `GET
  /api/v1/projects/{id}/exports/` lists past exports with a download URL.
- Three scheduled jobs via `CELERY_BEAT_SCHEDULE`: `notify_tasks_due_tomorrow`
  (the Phase 6 notification that needed a recurring check, not an event
  hook — now delivered), `generate_daily_project_reports` (reuses
  Phase 7's `get_project_statistics()` to notify each active project's
  owner with a daily digest), and `cleanup_expired_tokens` (wraps
  simplejwt's `flushexpiredtokens` management command to keep the
  `token_blacklist` tables from growing forever)
- **Caught and fixed a real latent bug from Phase 1**: `STORAGES` in
  `config/settings/base.py` only ever defined the `"staticfiles"` alias.
  Since Django 4.2, setting `STORAGES` replaces the framework's default
  dict wholesale rather than merging into it — so the `"default"` alias
  (what every plain `FileField`/`ImageField`, including `User.avatar` since
  Phase 2, resolves through) had been silently missing since the very first
  commit. It only surfaced now because Phase 8 is the first code that
  actually calls `.save()` on a `FileField`. Fixed by adding an explicit
  `"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}`
  entry.
- Verified against the real worker/beat containers, not `.delay()` calls
  assumed to work: confirmed the password-reset request returns in well
  under 100ms, polled a real `ProjectExport` row through PENDING →
  PROCESSING → COMPLETED as an actual worker process picked it up over
  Redis, read back and checked the generated CSV's contents, confirmed the
  `EXPORT_READY` notification arrived, and invoked all three scheduled
  tasks directly to confirm each produces the right notification/side
  effect.
- `runserver` is now genuinely ASGI/WebSocket-capable in development: with
  `daphne` first in `INSTALLED_APPS`, Channels overrides the `runserver`
  command itself — confirmed by the startup banner reading `Starting
  ASGI/Daphne ... development server`, no second dev-server process needed
- `config/asgi.py` upgraded from a plain `get_asgi_application()` call to a
  `ProtocolTypeRouter` — HTTP still goes straight to Django, WebSocket
  connections go through a custom `JWTAuthMiddlewareStack`
  (`config/channels_auth.py`) since Channels' stock auth middleware expects
  a session cookie this JWT-only API never sets
- `CHANNEL_LAYERS` on Redis DB 3 (`channels_redis`, already a dependency
  since Phase 1) — its own index, same reasoning as the cache/broker/result
  DB separation from Phases 7–8
- Two WebSocket endpoints, deliberately not one per model: `ws/projects/<id>/`
  (`apps.projects.consumers.ProjectConsumer`) relays that project's
  activity feed to every connected member, and `ws/notifications/`
  (`apps.notifications.consumers.NotificationConsumer`) relays one user's
  own notifications. Both re-check membership/identity at connect time —
  a WebSocket is just another way to read data, and it gets the same
  authorization the REST endpoints already enforce (a non-member's connect
  is rejected, verified directly)
- **No new call sites anywhere** — broadcasting was added centrally inside
  `ActivityService.log()` and `NotificationService.notify()`, so every
  existing event from Phases 3–8 (task created/assigned/status-changed,
  comments, membership changes, workflow changes, exports) is real-time for
  free. This is also what makes the spec's literal example — a task moving
  IN PROGRESS → DONE reaching other connected project members — already
  work: it's just a `task.status_changed` activity event like any other.
- Broadcasts are deferred via `transaction.on_commit()`, not fired inline —
  every calling service already wraps its write in `transaction.atomic()`,
  so broadcasting before commit could push a live event for a change a
  later failure in the same transaction rolls back.
- Verified against the real Redis-backed channel layer end-to-end using
  `channels.testing.WebsocketCommunicator` against the actual
  `config.asgi.application` (not a mock): a non-member's connection is
  rejected, an anonymous (no-token) connection is rejected, a member's
  connection is accepted, and a real assign + two real workflow
  transitions produce the exact activity events and notifications on the
  live socket, in order, with correct content.
- `GET /api/v1/search/` (`apps.analytics`, new — the app the original spec
  listed but nothing before this phase needed): PostgreSQL full-text search
  across project names/descriptions, task titles/descriptions, and comment
  bodies, ranked by `SearchRank` rather than substring matching. Every
  `Task`/`Project`/`Comment` got a stored `SearchVectorField` + `GinIndex`
  (populated by a `post_save` signal, the same pattern as Phase 7's cache
  invalidation) instead of computing `to_tsvector()` at query time on every
  request — searches use the index, they don't build it on the fly.
- `get_project_statistics()` gained the two metrics deferred from Phase 7:
  `average_completion_hours` and `tasks_completed_per_day`, both derived
  from `ActivityLog` (`task.status_changed` entries into a terminal state)
  rather than a stored `completed_at` column — `Task` has no such column
  because "completed" is entirely a function of workflow state, which is
  already source-of-truth data.
- **A real performance audit, not assumed cleanliness**: measured actual
  query counts (`CaptureQueriesContext`) for organizations/teams/workflows/
  labels/tasks list endpoints, first as a baseline, then compared 1 row vs.
  6 rows with assignees/labels attached. Result: every count was already
  flat regardless of row count — DRF's `PrimaryKeyRelatedField` has a
  built-in "pk-only" optimization that resolves a plain FK id without
  touching the database at all, so the `select_related`/`prefetch_related`
  choices made back in Phases 3–5 were already sufficient. No changes were
  needed to existing endpoints; the new `SearchView` was written with the
  same `select_related`/`prefetch_related` discipline from the start.
- Caught and fixed one real bug along the way (not in application code,
  in the phase's own smoke test): a test task's description literally
  contained the word "invoices" while asserting it *shouldn't* match a
  search for "invoice" — Postgres's stemming correctly matched it anyway.
  The search implementation was right; the test data was wrong.

- **A real frontend**: server-rendered HTML shells (Django `TemplateView`,
  zero ORM access — every view is `template_name` only) + Tailwind's Play
  CDN + vanilla JS ES modules calling `/api/v1/` exactly like an external
  consumer would. Pages: login, register, dashboard (organizations),
  organization detail (projects/teams/members), project detail (Kanban
  board, task detail slide-over, workflow configuration, activity feed,
  statistics charts), notifications, and search.
- A single `static/js/api.js` module is the *only* place that touches
  `fetch()`, JWT storage, or token refresh — every page imports it rather
  than reimplementing auth handling; a 401 triggers one silent refresh
  attempt before falling back to a redirect to `/login/`.
- The Kanban board uses native HTML5 drag-and-drop; dropping a card on a
  column POSTs a transition exactly like the button-based path in the task
  panel — there is no separate "is this move allowed" check on the
  frontend, because Phase 4 already made the backend the sole authority.
  An illegal drop is expected to be rejected by the API and is reported to
  the user, not prevented client-side.
- The Activity tab and the notification bell both hold a live WebSocket
  connection (Phase 9's `ws/projects/<id>/` and `ws/notifications/`) — a
  notification appearing in another browser tab with no reload was
  verified directly, not assumed from the backend tests alone.
- Statistics render as four Chart.js charts (tasks by priority, by
  workflow state, completed-per-day, workload by member) fed directly by
  Phase 7/10's `get_project_statistics()` response — no chart-specific
  backend endpoint was added.
- **Two real, security-relevant backend gaps were found and fixed while
  building the UI, before any frontend code shipped that would have
  exercised them**: `TaskSerializer` allowed `project` and `labels` to be
  changed via a plain `PATCH` with no validation at all — `TaskService`'s
  cross-project checks only ran on the *create* path
  (`TaskViewSet.perform_create`), since `ModelViewSet`'s default
  `update()` calls `serializer.save()` directly and never goes through the
  service layer. Fixed with `validate()`/`validate_labels()` on the
  serializer itself, so the guarantee holds regardless of entry point —
  verified with a script proving both a cross-project label attach and a
  project reassignment now return `400`.
- Small, additive API surface the UI needed and didn't have: a searchable
  user directory (`GET /api/v1/users/?search=`, for "invite by username"),
  `GET` support added to the existing `members` actions (previously
  POST-only) on organizations and projects, and `?organization=`/`?project=`
  filtering on Teams, Workflows, and Labels — all following the exact
  patterns already established for Tasks and Projects.
- **Verified with a real, driven browser** (Playwright/Chromium against
  the actual running `docker compose` stack), not just HTTP status checks:
  two independent browser sessions (as two different users) worked through
  the entire flow end-to-end — register, create an org, invite a second
  user, create a project, configure a workflow with states and a
  role-gated transition, create a task, move it through states, assign the
  second user, comment with an `@mention`, view statistics and activity —
  with zero browser console errors at any point. A second run specifically
  proved the role gate holds through the UI: a `DEVELOPER` clicking a
  `MANAGER`-only transition button gets a visible inline rejection and the
  task's status does not change.

### Engineering notes for Phase 11

**Django views for these pages do not touch the ORM — not even indirectly through a URL kwarg turned into template context.** Every route is `TemplateView.as_view(template_name="...")` with no `get_context_data()` override; a page like `/organizations/42/` renders the exact same static HTML regardless of whether organization 42 exists, and the `42` is read out of `window.location.pathname` by the page's own JS, not passed in by Django. This was a deliberate reading of the spec's "the frontend must consume the REST API instead of directly depending on Django ORM" — the strongest version of that rule is that the Django *view layer* for these pages has no ORM dependency to begin with, not just that some data happens to come from `fetch()`.

**One shared `api.js` module instead of each page reimplementing fetch/auth.** Token storage, the refresh-on-401 retry, and the error-envelope parsing (`config/exceptions.py`'s `{"error": {...}}` shape from Phase 5) all live in exactly one place. Every page — login, dashboard, organization detail, project detail, notifications, search — imports `{ api }` and calls `api.get`/`api.post`/etc.; none of them know or care that a 401 might trigger a silent token refresh behind the scenes.

**The Kanban board's drag-and-drop has no client-side legality check before the POST.** It would be easy to precompute "which columns can this card legally be dropped on" from the workflow's transitions and only allow those drops — but that duplicates the exact rule `WorkflowService.transition_task()` already enforces (Phase 4), and duplicated authority drifts: the frontend's copy of the rule and the backend's real rule can disagree the moment either changes. Instead, any drop is attempted, the backend is trusted to accept or reject it, and a rejection surfaces as a plain error to the user. The Playwright test for this (a `DEVELOPER` attempting a `MANAGER`-only transition through the actual UI, not a unit test of the service) is what actually proves the rule holds end-to-end, browser included.

**Two real bugs were caught by building the frontend, before any frontend code could exercise them in anger.** `TaskSerializer` had no server-side check stopping a `PATCH` from reassigning a task to a different project or attaching another project's label — `TaskService`'s validation only ran on creation. These are exactly the kind of gap that stays invisible until something actually issues that PATCH; the Kanban board's "add an existing label" feature was going to be the first code in the whole project to do so. Finding and fixing this while wiring up that one feature — rather than after shipping it — is the practical case for treating frontend work as integration testing for the API surface underneath it, not just presentation on top of it.

**`GET` added to existing `members` actions instead of new endpoints.** The organizations/projects `members` action was POST-only (invite) through Phase 6; the org/project pages need to list current members too. Rather than adding a separate `GET /organizations/{id}/member-list/`-style endpoint, the existing `@action(detail=True, methods=["post"], url_path="members")` became `methods=["get", "post"]` — one URL, one concept ("this endpoint is about project membership"), branching on `request.method` inside, matching the pattern `TaskViewSet.comments` already established back in Phase 5.

**A searchable user directory (`GET /api/v1/users/?search=`) trades a small amount of exposure for a workable invite flow.** Inviting someone requires knowing their numeric id, and no UI should ask an admin to go find that manually. Any authenticated user can search by username/email — deliberately not scoped to a shared organization, since the very first invite to a brand-new org has no shared organization yet to scope by. This is standard for this class of tool (Slack, Jira, Linear all have an unscoped member-search-to-invite flow); a stricter posture (visibility only after some prior relationship) is a reasonable production hardening step, noted here rather than applied, since nothing in the spec calls for it.

**Verified with an actually-driven browser, because a page returning `200` proves nothing about whether it works.** Every earlier phase's verification ran real requests against a real server and a real database; Phase 11 is no different in kind, just in tool — `curl`/`APIClient` can't click a drag handle or read a Chart.js canvas. Two independent authenticated browser sessions, `console --errors` checked at every step, and one deliberate negative test (the role-gate rejection) via the real UI is what actually stands behind "the frontend works," not a syntax check on the JS or a 200 from every route.

### Engineering notes for Phase 10

**A stored, indexed `search_vector` column instead of computing `SearchVector()` inside the query.** `Task.objects.annotate(search=SearchVector('title','description')).filter(search=query)` works with zero migrations, but Postgres has to tokenize every row's title+description on every single search request — no index can help because the index doesn't know what to index until the expression is fixed. Storing the vector as a real column with a `GinIndex` means a search is an index lookup, not a full-table tokenization pass — exactly the "document indexing decisions" the spec asks for, and the actual reason Postgres FTS is fast in production.

**Weighted vectors (`weight="A"` for title/name, `weight="B"` for description) instead of one flat `SearchVector`.** A query matching a task's title is a stronger relevance signal than one that only appears somewhere in a long description; `SearchRank` uses these weights to order results accordingly, so "invoice" ranks a task titled "Fix invoice bug" above one that merely mentions invoices in passing in its description.

**Search-vector maintenance is a `post_save` signal per model, mirroring Phase 7's cache-invalidation signals exactly.** The alternative — updating `search_vector` explicitly inside `TaskService.create_task`, `ProjectService.create_project`, `CommentService.add_comment`, and every update path — has the same failure mode Phase 7 already reasoned through: it works until something writes through the admin, a script, or a future code path that forgot to call it. A signal on the model makes "this row is searchable" a property of the table, not a list of call sites.

**A migration-time backfill (`RunPython`), not just the new field.** Adding `search_vector` as a plain nullable field leaves every pre-existing row with `search_vector = NULL` until its next `save()` — which might be never, for a row nobody edits again. Each of the three migrations backfills every existing row with the same `SearchVector` expression the signal uses going forward, so search coverage doesn't silently depend on "was this row touched after the migration ran."

**The performance audit measured before making any changes, and found the codebase already correct.** It would have been easy to "fix" `OrganizationViewSet`/`TeamViewSet`/`WorkflowViewSet`/`LabelViewSet` by adding `select_related()` calls that looked prudent by pattern-matching against Phase 5's `TaskViewSet` — and those changes would have been harmless, but pointless: DRF's `PrimaryKeyRelatedField.use_pk_only_optimization()` already avoids the query entirely for a plain FK-as-integer field by reading `instance.serializable_value(field)` (the raw `_id` column) instead of dereferencing the related object. The lesson generalizes: `select_related`/`prefetch_related` only matter for fields that actually need the *related object* (nested serializers, `SlugRelatedField`, or `.all()` on a many-relation) — which is exactly the set of places this project already had them (Task's assignees/labels, Workflow's states/transitions, ActivityLog's actor). Verifying this with `CaptureQueriesContext` rather than assuming it is the actual point of "performance optimization" as a discipline, not a checklist of `select_related()` calls to sprinkle everywhere.

### Engineering notes for Phase 9

**Two WebSocket endpoints, not a socket per model or a single do-everything socket.** The spec explicitly warns against turning every endpoint into a WebSocket. A project's activity feed and a user's personal notifications are the two things worth being real-time (they're exactly what a dashboard and a notification bell need to avoid polling) — everything else in the API (CRUD, statistics, exports) is still plain REST, requested on demand.

**WebSocket authorization mirrors REST authorization exactly, not a weaker version of it.** `ProjectConsumer.connect()` checks `ProjectMembership` the same way `ProjectViewSet.get_queryset()` does; a non-member's socket is rejected at connect time (verified directly: `connected is False`), not silently subscribed and then filtered. A WebSocket is one more way to read the same data, so it gets the same "never trust the frontend" treatment as everything else in this project.

**JWT-over-query-string, not Channels' session-based `AuthMiddlewareStack`.** Phase 5 chose stateless JWT bearer tokens specifically so the API doesn't depend on cookies or CSRF; a browser's WebSocket handshake can't set a custom `Authorization` header, so the access token travels as `?token=...` instead — the standard tradeoff for JWT-authenticated WebSockets. `config/channels_auth.py` validates it with the same `AccessToken` class DRF's `JWTAuthentication` uses.

**Broadcasting lives inside `ActivityService.log()` and `NotificationService.notify()`, not in every view/service that calls them.** This mirrors the exact reasoning from Phase 7's cache-invalidation signals: the property "an activity/notification that gets created also gets broadcast" belongs to the *service that creates the row*, not to a list of call sites (`TaskService`, `WorkflowService`, `CommentService`, `ProjectService`, `apps.projects.tasks`) that would otherwise all need to remember to add a broadcast call — and any future caller gets it for free, automatically, forever.

**`transaction.on_commit()` around every broadcast.** Every caller of these two services already runs inside `transaction.atomic()` (established back in Phases 3–4 specifically so multi-step writes are all-or-nothing). Broadcasting synchronously at the point of `.create()` would mean a live WebSocket event fires for a database row that might not exist a moment later, if something else in the same transaction fails and rolls it back. Deferring to `on_commit()` means a client only ever sees an event for a change that's actually, durably true — and outside of a transaction (a shell, a one-off script) `on_commit()` just runs immediately, so nothing had to special-case that.

**Known gap, deliberately left for Phase 12:** `config/wsgi.py` (used by `gunicorn` in a WSGI-only production deployment) has no path to WebSocket support — WSGI is fundamentally request/response, one connection per worker thread, with no long-lived bidirectional channel. `daphne` (already a dependency, already proven working via `runserver` in this phase) or another ASGI server needs to be what actually serves production traffic once WebSockets matter there; `docker-compose.yml`'s `web` service still runs Django's dev server today, which is explicitly documented as unfit for production regardless. This is Phase 12's "production Docker configuration" work, not deferred by oversight.

### Engineering notes for Phase 8

**A `ProjectExport` row, not a bare Celery task ID, is what the API returns and what the client polls.** A raw task ID ties the client to Celery's result backend and gives no natural place to attach a downloadable file, an error message, or a `created_at`/`completed_at` pair. A regular model row is queryable through the same permission/serializer machinery as everything else in the API (`GET /exports/` is scoped by project membership exactly like every other endpoint), survives a result-backend TTL expiring, and is visible in the admin without any extra tooling.

**The export task records `FAILED` + `error_message` on the row instead of only raising.** A task that just raises leaves Celery's result backend as the only record of what happened, and nothing in this project surfaces worker exceptions to an end user. Catching the exception, writing it to the row, and re-raising (so it's still visible in worker logs / Celery's own failure tracking) means `GET /exports/` can show *why* an export failed, not just that it's stuck in `PENDING` forever.

**The Celery Beat schedule lives in Python (`CELERY_BEAT_SCHEDULE` + the default file-based `PersistentScheduler`), not `django-celery-beat`.** `django-celery-beat` earns its place when non-developers need to add/edit schedules at runtime through the admin — it ships its own models and migrations for exactly that. Three fixed, developer-authored jobs don't need that; adding the package now would be exactly the "unnecessary dependency" the project's own engineering rules call out, for a capability (runtime-editable schedules) nothing here asks for.

**The Phase 1 `STORAGES` bug is a good example of why later phases keep re-verifying earlier ones with real execution.** `manage.py check` and every prior phase's smoke test passed cleanly for seven phases because nothing had tried to write to a `FileField` yet — `User.avatar` was always optional and never exercised, and Django's system checks don't validate that `STORAGES["default"]` exists until something actually resolves it. The bug was real from commit one; it just had no code path willing to trigger it until now.


**Statistics are computed from Postgres on a miss, served from Redis on a hit — cache-aside, not write-through.** The alternative (recomputing and writing to cache on every task mutation) would mean paying the aggregation cost on every write whether or not anyone is currently looking at that project's dashboard. Cache-aside only pays that cost when a read actually happens after data changed, which matches the real access pattern (dashboards are viewed far less often than tasks are edited).

**Invalidation is signal-driven, not TTL-only.** A 5-minute TTL alone would mean statistics can be up to 5 minutes stale after every single write — acceptable for some products, not really "cache-aside done right" for a project dashboard someone might refresh right after assigning a task. `post_save`/`post_delete` signals on `Task` and `TaskAssignment` delete the specific project's cache key the moment a relevant write commits, so the very next read recomputes fresh data; the TTL still exists purely as a safety net against a write path a signal doesn't cover, not as the primary mechanism.

**Signals, not service-layer `cache.delete()` calls, because the invariant is about the *data*, not the *code path*.** `TaskService.create_task`, `TaskService.assign`, and `WorkflowService.transition_task` all already write `Task`/`TaskAssignment` rows; adding an explicit `invalidate_project_statistics()` call to each of them would work today, but would silently stop working the moment someone edits a task through the Django admin, a management command, or a future Celery task that doesn't happen to call the same service function. A `post_save`/`post_delete` signal on the model itself invalidates the cache no matter which code wrote the row — the correctness property ("the cache reflects the database") is attached to the table, not to a list of call sites someone has to remember to keep updated.

**A dedicated Redis DB index (2) for the cache, distinct from the Celery broker (0) and result backend (1).** All three currently point at the same Redis *server* — there's no operational need for separate servers yet — but keeping them on separate logical DBs means a development-time `FLUSHDB` on the cache (a completely reasonable thing to do while iterating) can't accidentally wipe a pending Celery queue, and vice versa.

**Django's built-in `RedisCache` instead of adding `django-redis`.** Since Django 4.0, `django.core.cache.backends.redis.RedisCache` wraps `redis-py` directly and covers everything this project needs (`get`/`set`/`delete` with a TTL) — `redis` was already a dependency for Channels/Celery, so reaching for `django-redis` on top of it would be exactly the kind of unnecessary dependency the project's own engineering rules warn against. `django-redis` earns its place when you need its extras (native `delete_pattern`, per-key client-side compression, multiple named cache backends with different serializers) — none of which apply here.


**`ActivityLog` immutability is enforced in `save()`/`delete()`, not just admin config.** `Meta` options like `editable=False` or hiding the model from `ModelAdmin` only stop casual edits through Django's own UI; anyone with ORM access (a script, a shell, a future admin action someone adds without checking the model) would otherwise still be able to call `.save()` on an existing row. Raising in `save()` when `self.pk is not None`, and unconditionally in `delete()`, makes tampering a hard `ValueError` from any code path — verified directly by mutating a real row's `action` field and confirming it raises rather than silently succeeding.

**`GenericForeignKey` for the audit target, direct FKs for the tenant-scoping fields.** `ActivityLog` needs to point at *any* loggable model (`Task`, `Comment`, `ProjectMembership`, `Workflow`) — a `GenericForeignKey` via `django.contrib.contenttypes` means adding a new loggable model later never requires a migration on `ActivityLog` itself. But `organization` and `project` are still plain FKs, not derived from the generic target at query time: the dominant read pattern is "this project's activity feed, ordered by time," and that needs to be answerable with one indexed filter, not a join that starts from an arbitrary content type.

**Workflow-authoring events (`create_workflow`, `add_state`, `add_transition`) log at the organization level (`project=None`), not the project level.** A `Workflow` can be attached to multiple projects (or none yet) — logging it against "the project" would require picking one arbitrarily, or duplicating the log row per attached project. The organization is the actual owner of a `Workflow` in the data model, so that's where its change history belongs; `GET /api/v1/projects/{id}/activity/` still surfaces task/comment/membership events scoped to that specific project correctly, because those *do* have one unambiguous project.

**`@mention` notifications only fire for usernames that resolve to an actual project member.** `MENTION_RE.findall()` on a comment body is untrusted user input — someone could type `@anyone_at_all`. Cross-referencing matched usernames against `ProjectMembership` before calling `NotificationService.notify()` means a typo or an attempt to spam an arbitrary account with notifications simply produces no notification, rather than trusting free text as a delivery target.

**Every side effect lands inside the same `transaction.atomic()` as the change that caused it — no new transactions were opened for Phase 6.** This was the whole point of wrapping `TaskService.create_task`, `WorkflowService.transition_task`, etc. in `transaction.atomic()` back in Phases 3–4 even when they were single-statement at the time: Phase 6 only had to *add statements inside the existing block*, not restructure anything. A task assignment that fails to write its `Notification` (a constraint violation, a bug) rolls back the `TaskAssignment` too — there's no state where the database shows an assignment that nobody was ever notified about because of a partial write.


**IDOR protection is a `get_queryset()` filter, not a per-request ownership check.** Every viewset's `get_queryset()` restricts rows to what the requesting user is actually a member of (`Organization.objects.filter(memberships__user=self.request.user)`, and similarly for projects/tasks/workflows/labels). Because DRF's `get_object()` calls `get_queryset().get(pk=...)`, requesting another tenant's `/api/v1/projects/16/` doesn't fail a permission check — the row is never in the queryset in the first place, so it 404s. This was verified directly: a non-member fetching another org's resource gets `404`, not `403` — the *not found* response is deliberate, since a `403` would confirm the resource exists at all (an enumeration leak the spec's IDOR requirement is really about).

**JWT via `djangorestframework-simplejwt`, with rotation + blacklisting on logout.** Access tokens are short-lived (30 min); refresh tokens rotate on every use and the old one is blacklisted (`rest_framework_simplejwt.token_blacklist`, its own app with its own migrations). This means a stolen refresh token has a narrow window before the legitimate client's next refresh invalidates it, and `POST /auth/logout/` (explicitly blacklisting the current refresh token) actually revokes a session rather than just discarding a token client-side — verified by confirming a refresh attempt fails with `401` immediately after logout.

**Password reset returns `200` whether or not the email matches an account.** A reset endpoint that returns `404` for an unknown email (or a differently-shaped success response) lets an attacker enumerate every registered email address one guess at a time. Returning an identical response either way costs nothing for legitimate users and closes that leak — a small decision, but exactly the kind the spec's IDOR/security section is checking for.

**`workflow_state` is a `read_only_field` on `TaskSerializer` — the only way to change it is `POST /tasks/{id}/transition/`, which calls `WorkflowService.transition_task()`.** A plain `PATCH /tasks/{id}/ {"workflow_state": 9}` would bypass every rule built in Phase 4 (sequential transitions, role gating, project-membership checks) — the serializer field being read-only isn't an oversight, it's what makes the workflow engine's backend authority actually hold at the API layer, not just in a script that happens to call the service correctly.

**A prefetch-cache bug was caught by testing through the real view, not by calling the service directly.** `TaskViewSet.get_object()` evaluates a queryset with `prefetch_related("assignees")` *before* the `assign` action calls `TaskService.assign()`; the instance's cached (empty) assignee list doesn't know a write just happened underneath it, so the response echoed stale data even though the database was correct. The fix is `task.refresh_from_db()` (which clears Django's `_prefetched_objects_cache`) before re-serializing. This is exactly the class of bug integration-level testing exists to catch — a unit test of `TaskService.assign()` alone would have passed.

**Rate limiting has a separate `"auth"` throttle scope, tighter than the general anonymous rate.** `register`/`login`/`password-reset` sit behind `ScopedRateThrottle` at `20/hour`, distinct from the general `anon: 100/day`. Credential-stuffing and account-enumeration attempts concentrate on exactly these endpoints, so throttling them separately means the general anonymous browsing rate doesn't have to be squeezed uncomfortably tight just to also cover login attempts.

**A custom `EXCEPTION_HANDLER` wraps every DRF error in one `{"error": {...}}` shape.** Without it, a `ValidationError` produces a bare list/dict, a `PermissionDenied` produces `{"detail": "..."}`, and a throttle produces yet another shape — three different response bodies an API client would need to special-case. `config/exceptions.py` normalizes all of them to `{"error": {"status_code": ..., "detail": ...}}` once, centrally.

### Engineering notes for Phase 4

**Workflow states and transitions are database rows, not a hardcoded `Task.status` enum.** The obvious shortcut — `Task.status = models.CharField(choices=[...])` — would work for one fixed pipeline, but the spec requires administrators to define their own per-organization workflow (different teams genuinely do run BACKLOG→TODO→DONE vs. a six-stage review pipeline). Modeling `Workflow`/`WorkflowState`/`WorkflowTransition` as real tables makes the pipeline itself configurable data instead of code that needs a migration to change.

**`Project.workflow` and `Task.workflow_state` were deliberately left off in Phase 3 and added now as their own migrations.** Adding a FK to a model that doesn't exist yet isn't possible, and bolting a placeholder field on early (nullable FK to a future app) would mean either an awkward string reference to nothing or a throwaway migration to delete later. Waiting until `WorkflowState` was real and doing a normal additive migration (`projects.0002_project_workflow`, `tasks.0002_task_workflow_state_and_more`) is the same operation any team does when a real product grows a new relationship — nothing here needed a special case.

**`WorkflowTransition.allowed_roles` is a Postgres `ArrayField`, not a join table.** The roles allowed to perform one transition are a small, unordered, attribute-less set of strings scoped entirely to that transition row — there's no case where you'd query "all transitions with role X" independently of a specific workflow, which is the situation that would justify a normalized `TransitionAllowedRole` join table. `ArrayField` is a Postgres-specific feature (this project's rationale for choosing Postgres over MySQL/SQLite in the first place) used here because it's the right fit, not just to show it exists. Role strings are validated in `WorkflowService.add_transition` against `ProjectMembership.Role`, not via Django `choices=` on the field — Postgres doesn't enforce `choices` at the DB level regardless, and importing `apps.projects` into `apps.workflows.models` for the choices list would create a circular import (`apps.projects.models.Project.workflow` already points back at `apps.workflows.Workflow`).

**`WorkflowService.transition_task()` re-derives every fact from the database on every call — it never trusts a `from_state` the caller might pass in.** The one non-obvious rule: a task with `workflow_state = None` may only move to a state marked `is_initial=True`, and that specific move requires no `WorkflowTransition` row (there's no "from" state to look one up by) — just current project membership. Every subsequent move requires an actual `WorkflowTransition(workflow, from_state, to_state)` row to exist, and if it does, the caller's `ProjectMembership.role` must appear in that transition's `allowed_roles` (an empty list means "any project member"). This was verified by executing all four failure modes directly: entering at a non-initial state, skipping a state with no transition row, attempting a transition without the required role, and attempting one as a non-project-member — each raises, none silently no-ops.

**The unique constraint on `WorkflowTransition(workflow, from_state, to_state)` doubles as the lookup index.** Postgres builds a btree for every unique constraint, and `(workflow, from_state, to_state)` as a leftmost-prefix already covers `transition_task()`'s query pattern (`workflow=..., from_state=..., to_state=...`) — adding a separate `Meta.indexes` entry for the same columns would just be a second index maintaining the same information.

### Engineering notes for Phase 3

**`Project.slug` is unique per-organization (`UniqueConstraint(organization, slug)`), not globally unique.** Two unrelated tenants both naming a project "backend" is normal and shouldn't collide; project URLs are scoped under their organization (`/organizations/<org>/projects/<project>/`) anyway, so global uniqueness would be an artificial constraint that exists only to serve a URL scheme this app doesn't use.

**Two different `on_delete` policies for "ownership" vs. "attribution" foreign keys.** `Project.owner` (like `Organization.owner`) uses `PROTECT` — a project needs exactly one accountable owner, and losing that without an explicit reassignment is a bug. `Task.created_by` and `Comment.author` use `SET_NULL` instead — these are high-cardinality attribution fields on child records, and blocking every user deletion because they once filed a task or left a comment would make account deletion impractical in any real usage. The task/comment is worth keeping even if authorship is lost.

**Authorization lives in the service layer, not a DB constraint, for cross-table invariants Postgres can't express declaratively.** "A project's owner must be an organization member," "a task assignee must be a project member," "a label must belong to the same project as the task it's attached to" — none of these are expressible as a single-table `CHECK` or `UniqueConstraint`; they're relationships across tables. `ProjectService`, `TaskService`, and `CommentService` enforce them with plain `ValueError`s before any write happens. This is deliberately *not* yet wired into DRF permission classes (Phase 5) — the point of Phase 3 is that these rules hold even called directly (from the admin, a script, a future Celery task), not only when a particular view remembers to check.

**Verified by executing the failure paths, not just the happy path.** The Phase 3 smoke test doesn't stop at "a task can be created" — it asserts that creating a project as a non-member raises, that assigning a non-member raises, and that attaching a label from a different project raises. A service function that silently permits a cross-tenant write is a security bug, so the thing worth demonstrating is that it *doesn't*.

### Engineering notes for Phase 2

**Custom `User` model set up in Phase 1's `AUTH_USER_MODEL`, populated
now.** Swapping the user model after the first `migrate` touches every
foreign key that points at `auth.User`, so `AUTH_USER_MODEL = "accounts.User"`
had to exist before any migration ran — this is why `apps.accounts` was the
very first app.

**`Organization.owner` uses `on_delete=PROTECT`, not `CASCADE`.** Deleting a
user who still owns organizations should fail loudly rather than silently
deleting (or orphaning) those organizations — ownership transfer should be
an explicit action, not a side effect of removing an account. This was
verified directly: attempting to delete a user with an owned organization
raises `ProtectedError` from Postgres-backed FK enforcement.

**`OrganizationService.create_organization` wraps two inserts in
`transaction.atomic()`.** An `Organization` row without its owner's `OWNER`
`Membership` row would leave the creator locked out of the org they just
made. Wrapping both writes means either both commit or neither does — this
logic lives in a service function, not the (not-yet-built) view/serializer,
so it's reusable from the API, the admin, and a management command alike.

**Composite index on `Membership(organization, role)`.** The most common
authorization query in a multi-tenant app is "does this user have at least
role X in this organization" — indexing the (organization, role) pair
directly supports that filter instead of relying on a full-table scan or an
index on `organization` alone.

**`UniqueConstraint`s over `unique_together`.** `unique_together` is
Django's older, soon-to-be-fully-deprecated API; `UniqueConstraint` in
`Meta.constraints` is the current recommended way to declare the same
database-level guarantee (one membership per user per organization, one
team name per organization, one membership per user per team).

## Repository Structure

```
backend-dbms/
├── config/
│   ├── settings/
│   │   ├── base.py          # shared settings
│   │   ├── development.py   # DEBUG=True, permissive CORS/hosts
│   │   └── production.py    # hardened: HSTS, secure cookies, SSL redirect
│   ├── urls.py
│   ├── api_router.py           # aggregates every app's DRF router under /api/v1/
│   ├── routing.py               # aggregates every app's websocket_urlpatterns
│   ├── channels_auth.py          # JWT-from-querystring auth for WebSocket handshakes
│   ├── exceptions.py            # shared DRF exception handler -> {"error": {...}}
│   ├── asgi.py                # ProtocolTypeRouter: HTTP -> Django, WebSocket -> Channels
│   ├── wsgi.py
│   └── celery.py
├── apps/
│   ├── accounts/              # custom User model + api/ + tasks.py (password reset email, token cleanup)
│   ├── organizations/         # Organization, Membership, Team, TeamMembership + api/ + management/commands/seed_data.py
│   ├── workflows/             # Workflow, WorkflowState, WorkflowTransition + api/
│   ├── projects/              # Project, ProjectMembership, ProjectExport + api/ + statistics.py, caching.py, tasks.py, consumers.py, search.py, signals.py
│   ├── tasks/                 # Task, Label, TaskAssignment + api/ + signals.py (cache invalidation + search vector) + tasks.py (due-soon reminders) + search.py
│   ├── comments/              # Comment + api/ (serializer only; surfaced via tasks/{id}/comments/) + search.py, signals.py
│   ├── activity/              # ActivityLog (immutable audit trail) + api/ (serializer only) + realtime.py
│   ├── notifications/         # Notification + api/ + consumers.py, realtime.py
│   └── analytics/             # api/ only, no models — GET /api/v1/search/ (cross-model full-text search)
├── templates/                 # base.html + one shell per page, zero ORM access from any view
│   ├── base.html               # nav (search box, notification badge, logout)
│   ├── login.html / register.html
│   ├── dashboard.html          # organizations
│   ├── organization_detail.html # projects, teams, members
│   ├── project_detail.html     # Kanban board, task panel, workflow config, activity, statistics
│   ├── notifications.html
│   └── search.html
├── static/
│   ├── css/app.css             # kanban layout + drag-and-drop affordances; everything else is Tailwind
│   └── js/
│       ├── api.js               # the only module that touches fetch()/JWT storage/token refresh
│       ├── nav.js                # shared header: search box, live notification badge (WebSocket)
│       └── pages/                # one module per template, imports api.js, nothing else does
├── tests/                      # pytest — 78 tests, ~90% coverage of apps/ (see Testing below)
├── docker/
│   └── entrypoint.sh          # waits for Postgres before running the app command
├── manage.py
├── docker-compose.yml          # development: bind-mounted source, runserver, ports published
├── docker-compose.prod.yml     # production: daphne, no bind mount, non-root, ports restricted
├── Dockerfile                  # non-root user, build-time collectstatic
├── .env.example
├── .env.production.example
├── pyproject.toml             # dependencies, managed with uv
└── README.md
```

## Technology Stack

Python · Django · Django REST Framework · PostgreSQL · Redis · Celery ·
Django Channels · Tailwind CSS (Play CDN) · Chart.js · Docker Compose ·
pytest / pytest-django

Dependency management uses [`uv`](https://docs.astral.sh/uv/) — `pyproject.toml`
+ `uv.lock` are the source of truth; there is no `requirements.txt`.

## Why these Phase 1 choices

**Split settings (`base` / `development` / `production`) instead of one
`settings.py` with `if DEBUG` branches.** Keeps production-only hardening
(HSTS, secure cookies, mandatory `SECRET_KEY`/`ALLOWED_HOSTS`) physically
separate from development conveniences, so a env misconfiguration can't
silently disable a security setting — `production.py` raises at import time
if `SECRET_KEY` or `ALLOWED_HOSTS` is missing, rather than falling back to
something insecure.

**`DATABASE_URL` via `dj-database-url` instead of five separate
`POSTGRES_*` settings.** One connection string is easier to keep correct
across local dev, Docker Compose, and (eventually) a hosting provider that
injects its own `DATABASE_URL`. `docker-compose.yml` still needs the
individual `POSTGRES_*` vars for the `db` service's own bootstrap, so both
are kept in `.env.example` and cross-referenced.

**`psycopg` 3 (`psycopg[binary]`) over `psycopg2`.** psycopg2's binary wheel
distribution is officially discouraged for anything beyond local dev,
whereas psycopg 3 ships a supported binary wheel and has been Django's
recommended driver for `django.db.backends.postgresql` since Django 4.2.

**Celery app configured now, no tasks yet.** `config/celery.py` and the
`CELERY_*` settings are wired up in Phase 1 purely so nothing about the
Django settings module has to change when Phase 8 (background jobs) starts
— only `docker-compose.yml` needs a new `worker`/`beat` service at that
point.

**Third-party apps (`rest_framework`, `corsheaders`, `django_filters`,
`drf_spectacular`, `channels`) registered in `INSTALLED_APPS` already.**
Registering an app just makes Django aware of it; it has no behavior until
its settings are configured, which happens in the phase that actually uses
it (DRF config in Phase 5, CORS origins once there's a frontend, Channels
routing in Phase 9). Doing the registration now avoids touching
`INSTALLED_APPS` repeatedly.

## Environment Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django cryptographic signing key. Required (non-empty) in production. |
| `DEBUG` | Django debug mode. `True` locally, must be `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated hostnames Django will serve. |
| `DATABASE_URL` | Full Postgres connection string, parsed by `dj-database-url`. |
| `POSTGRES_DB/USER/PASSWORD/PORT` | Used by the `db` container itself and to build `DATABASE_URL` inside Compose. |
| `REDIS_URL` | Base Redis connection, used for cache/Channels layer in later phases. |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Separate Redis DB indexes for the Celery broker vs. task results, so they don't share keyspace. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API cross-origin (production only; dev allows all). |

Secrets are never committed — `.env` is git-ignored, `.env.example` holds
only placeholder/dev-safe values.

## Running the Project

### Option A — Docker Compose (recommended; matches production topology)

```bash
cp .env.example .env
docker compose up --build
```

This starts Postgres, Redis, the Django dev server (`0.0.0.0:8000`), a
Celery worker, and Celery Beat. Every service's entrypoint
(`docker/entrypoint.sh`) waits for Postgres to accept connections before
running its own command, so `docker compose up` from a cold start doesn't
race the database container — including the worker, which touches the
database from inside its tasks.

Verify everything is healthy:

```bash
docker compose ps                              # web, worker, beat all "Up"
docker compose exec web python manage.py check
docker compose logs worker --tail 20           # should list every autodiscovered task
```

### Option B — Local (uv-managed virtualenv), Postgres running separately

```bash
uv sync
cp .env.example .env               # point DATABASE_URL at your local Postgres
uv run python manage.py check
```

`uv sync` installs everything declared in `pyproject.toml` (already present
in this repo: Django, DRF, Celery, Channels, psycopg, redis, drf-spectacular,
etc.) into `.venv`.

Once dependencies are installed and a database is reachable, apply
migrations:

```bash
uv run python manage.py migrate
```

Once running, open **http://localhost:8000/register/** in a browser for
the actual application (dashboard → organizations → projects → Kanban
board, workflow configuration, activity feed, statistics, notifications,
search). The API itself is browsable at `/api/v1/` (e.g.
`/api/v1/organizations/`) and documented at `/api/docs/` (Swagger UI) /
`/api/schema/` (raw OpenAPI). A minimal end-to-end flow via `curl`, for
testing the API directly:

```bash
curl -X POST localhost:8000/api/v1/auth/register/ -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"S3curePass!23"}'

curl -X POST localhost:8000/api/v1/auth/login/ -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"S3curePass!23"}'
# -> {"refresh": "...", "access": "..."}

curl localhost:8000/api/v1/organizations/ -H "Authorization: Bearer <access>"
```

Also worth trying a real WebSocket connection once the stack is up:

```js
const token = "<a valid JWT access token from /api/v1/auth/login/>";
const ws = new WebSocket(`ws://localhost:8000/ws/projects/1/?token=${token}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

## Testing

```bash
uv sync                              # installs dev dependencies too (pytest, pytest-django, pytest-cov)
cp .env.example .env                 # point DATABASE_URL/REDIS_URL etc. at your Postgres/Redis
uv run python -m pytest              # runs against a real Postgres test database, created/dropped automatically
uv run python -m pytest --cov --cov-report=term-missing   # with a coverage report
```

Tests run from the host (`uv run`), not inside the `web`/`worker` containers — those images deliberately exclude dev dependencies (`uv sync --no-dev` in the Dockerfile) to keep the runtime image lean, matching the project's own "no unnecessary dependencies" rule. `pytest-django` creates and migrates a throwaway `test_<db>` database against whatever `DATABASE_URL` resolves to, so pointing `.env` at the Dockerized Postgres (the default) is enough — no separate test database setup.

**78 tests, ~90% coverage of `apps/`,** organized by what the spec's testing section asks for specifically, not by file:

| File | Covers |
|---|---|
| `test_models.py` | Constraints, `PROTECT`/`SET_NULL` behavior, `ActivityLog` immutability |
| `test_auth_api.py` | Register/login/refresh/logout, password hashing, enumeration-safe password reset |
| `test_organizations_api.py`, `test_tasks_api.py`, `test_workflow_config_api.py` | CRUD, permissions, filtering, search, pagination |
| `test_workflow_transitions.py` | The workflow engine's business logic directly (valid/invalid/role-gated transitions) |
| `test_security_idor.py` | Dedicated cross-tenant access tests — every major resource, 404 not 403 |
| `test_transactions.py` | `transaction.atomic()` actually rolls back on a simulated mid-block failure |
| `test_statistics.py` | `get_project_statistics()`'s aggregation logic and cache hit/miss behavior |
| `test_exports.py` | The Celery export task, run synchronously via `CELERY_TASK_ALWAYS_EAGER` |
| `test_websocket_consumers.py` | Real `WebsocketCommunicator` against the real ASGI app and Redis channel layer |
| `test_comments_and_mentions.py`, `test_periodic_tasks.py`, `test_notifications_and_activity.py` | The remaining service-layer business logic |
| `test_performance.py` | Formalizes Phase 10's manual query-count check into a real regression test |
| `test_seed_data.py` | The seed command itself (this is what caught the `--clear` bug below) |

An autouse fixture (`tests/conftest.py`) clears the Redis cache before every test — Postgres state rolls back automatically per test (pytest-django wraps each in a transaction), but Redis doesn't, so without this, throttle counters and cached statistics would leak between tests and make results depend on run order.

Two real bugs were caught specifically because these are integration tests hitting real Postgres/Redis, not because a human happened to think of them:

1. **`transaction.on_commit()` callbacks never fire under pytest-django's default transaction-wrapped tests.** `test_websocket_consumers.py` needed `pytest.mark.django_db(transaction=True)` (real commits, not rollback) to actually exercise the Phase 9 real-time broadcast path — a plain `@pytest.mark.django_db` test would have silently never triggered the broadcast and given a false sense of coverage.
2. **`CELERY_TASK_ALWAYS_EAGER` set via pytest-django's `settings` fixture had no effect.** Celery reads `CELERY_*` Django settings once, when `config/celery.py`'s `app.config_from_object()` runs at import time; overriding `django.conf.settings` afterward doesn't reach an already-instantiated `Celery` app object. Fixed by mutating `celery_app.conf` directly in the test fixture instead.

## Security Review

A pass against the spec's security checklist, in the order it's written there:

- **CSRF**: the API is JWT-authenticated (Phase 5), not session-authenticated, so it's correctly CSRF-exempt by construction; Django admin still goes through `CsrfViewMiddleware` normally. `production.py` sets `CSRF_COOKIE_HTTPONLY` and requires `CSRF_TRUSTED_ORIGINS` to be configured for a real domain.
- **Password hashing**: Django's default PBKDF2 hasher via `create_user()` everywhere — verified directly in `test_auth_api.py` (`user.password != raw_password`, `user.check_password(raw_password)`).
- **Permission checks / IDOR**: every list/detail endpoint scopes its queryset to the caller's actual memberships; a non-member gets `404`, never `403` (`test_security_idor.py`, 8 dedicated tests across projects, tasks, activity, statistics, comments, notifications, and search).
- **Input validation**: DRF serializers reject malformed input by default; `validate_password` enforces Django's password validators on register/reset; `TaskSerializer.validate_labels()`/`validate()` (below) close a gap that plain field validation wouldn't have caught.
- **Safe file uploads**: the API accepts **no user-uploaded files at all** — `UserSerializer` marks every field (`avatar` included) read-only, and `ProjectExport.file` is only ever written by the Celery export task server-side. This is a deliberate scope boundary, not an oversight: there's no upload path to secure because there's no upload path.
- **Rate limiting**: Redis-backed (Phase 7) `DEFAULT_THROTTLE_CLASSES` globally, with a tighter dedicated `"auth"` scope (20/hour) on register/login/password-reset specifically (Phase 5).
- **Secure HTTP config for production**: `production.py` — HSTS (with subdomains + preload), `SECURE_SSL_REDIRECT`, secure+HttpOnly cookies, `X_FRAME_OPTIONS: DENY`, `SECURE_CONTENT_TYPE_NOSNIFF`, and (new this phase) the browsable API's HTML renderer disabled in favor of JSON-only.
- **Environment variables for secrets / no hardcoded credentials**: confirmed `.env`/`.env.production` are git-ignored and were never staged; `SECRET_KEY` has no production fallback (raises if unset); grepped the codebase for `.raw(`/`cursor.execute(`/hardcoded `SECRET_KEY =` — none outside the documented dev-only placeholder in `development.py`.

**Two real, previously-undetected issues were found and fixed during this pass:**

1. **Stored XSS via `Label.color`.** The Kanban board's label picker (`project_detail.js`) interpolates a label's color directly into an HTML `style` attribute. `Label.color` had no format validation beyond a length limit — a value like `red" onmouseover="alert(1)` would have broken out of the attribute and injected an event handler, persisted in the database, executing for every viewer of that label. Fixed at the source: a `RegexValidator` on the model (`^#[0-9A-Fa-f]{6}$`), which DRF's `ModelSerializer` picks up automatically for the API too, plus a matching client-side format check in the JS as defense in depth (in case a future relaxation of the backend constraint, or any other data source, ever bypasses it).
2. **`TaskSerializer` allowed changing a task's `project` or attaching another project's `label` via a plain `PATCH`.** `TaskService`'s cross-project checks only ran on the create path (`TaskViewSet.perform_create`); `ModelViewSet`'s default `update()` calls `serializer.save()` directly and never touches the service layer. Found and fixed while building the Kanban board's "add a label" feature in Phase 11 — before any shipped frontend code could have exercised the gap. Fixed with `validate()`/`validate_labels()` on the serializer itself, so the guarantee holds regardless of entry point.

**Known, accepted tradeoffs** (documented rather than fixed, since nothing in the spec calls for closing them and doing so would add scope disproportionate to this project):

- `GET /api/v1/users/?search=` is an unscoped user directory available to any authenticated user (Phase 11) — needed so inviting someone to a brand-new organization doesn't require already knowing their numeric id. Standard for this class of tool (Slack/Jira/Linear all work this way); a stricter posture (visibility only after a prior relationship) is a reasonable hardening step for a real deployment, not applied here.
- Django admin's login form has no rate limiting (Django's own limitation, not this project's) — DRF throttling only covers the `/api/v1/` surface. Adding brute-force protection there (`django-axes` or similar) would be a new dependency for a surface normally restricted to trusted staff, not the same threat model as the public API.

## Production Deployment

```bash
cp .env.production.example .env.production   # fill in every value — production.py refuses to start otherwise
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

Differences from `docker-compose.yml` (development), and why:

- **`web` runs `daphne -b 0.0.0.0 -p 8000 config.asgi:application`, not Django's dev server.** Channels' documented production ASGI server, serving both plain HTTP and the `ws/` WebSocket endpoints (Phase 9) from the same process — Django's dev server is explicitly unfit for production regardless of Channels, and a WSGI server (`gunicorn`, which this project no longer depends on) has no path to WebSocket support at all.
- **No source bind-mount.** The image is deployed as built — static files are already collected at build time (below), so there's nothing left for a live volume to override.
- **`DJANGO_SETTINGS_MODULE=config.settings.production`**, which enforces `SECRET_KEY`/`ALLOWED_HOSTS` are actually set and turns on the HSTS/secure-cookie/HTTPS-redirect hardening from the Security Review above.
- **Postgres/Redis ports are not published to the host** — only `web` needs to be reachable, and only through a TLS-terminating reverse proxy in front of it (not included here; this compose file assumes one exists upstream).
- **The `Dockerfile` itself** runs `collectstatic` at build time (against a throwaway placeholder `SECRET_KEY`/`ALLOWED_HOSTS` — static file hashing uses file content, not `SECRET_KEY`, so this is safe) and drops to a non-root `app` user for every container, dev included.
- **A named `media_data` volume**, not a bind mount, for `MEDIA_ROOT`. This was caught by actually testing the non-root change: a bind-mounted host directory doesn't carry the container's file ownership, so the non-root `app` user got a `PermissionError` writing a Celery export's CSV until this was added. Source code still bind-mounts for dev hot-reload; only this one runtime-writable subdirectory is a named volume instead.

## Seed Data

```bash
docker compose exec web python manage.py seed_data          # idempotent: skips orgs that already exist
docker compose exec web python manage.py seed_data --clear  # wipes previously seeded demo orgs first
```

Creates 3 demo organizations (10 shared users, password `DemoPass123!` for all), each with teams, a full workflow (Backlog → Todo → In Progress → Code Review → Done, with a manager-gated final approval), 3 projects, and ~10 tasks per project — assigned, labeled, commented on, and walked partway through the workflow at random. Every row goes through the same service layer the API uses (`OrganizationService`, `ProjectService`, `TaskService`, `WorkflowService`, `CommentService`), not raw `.objects.create()` calls, so seeding also exercises — and produces realistic — `ActivityLog` entries and `Notification`s exactly as if a real user had done all of it by hand.

`--clear` deletes `Project`s (and everything that cascades from them: `Task`, `Comment`, `Label`) before deleting `Organization`s — deleting organizations directly hit a real `ProtectedError`, since `Task.workflow_state` is `PROTECT` and blocked the cascade into `Workflow` while tasks still existed. `tests/test_seed_data.py` locks this in.

## Future Improvements

Honest gaps, not covered elsewhere in this README as a "Phase N deferred" note:

- **Sprints** (`apps/sprints` in the original architecture) were never built — nothing in the 12-phase plan specifically required them, and the project already demonstrates the same relational/service-layer patterns (Teams, Workflows) they would have repeated.
- **Object storage for media** (S3-compatible) instead of a local named volume — fine for a single-host deployment, not for a horizontally-scaled one where `web`/`worker` might run on different machines.
- **`django-celery-beat`** for admin-editable schedules, if the three fixed periodic jobs (Phase 8) ever need to become user-configurable rather than developer-authored.
- **A stricter, org-scoped user directory** in place of the current unscoped `GET /api/v1/users/?search=` (see Security Review's accepted tradeoffs).
- **Brute-force protection on Django admin's login** (`django-axes` or equivalent) if admin is ever exposed beyond a trusted internal network.
- **CI** (GitHub Actions or similar) running `pytest` and `manage.py check --deploy` on every push — the test suite exists and passes; nothing currently runs it automatically.
