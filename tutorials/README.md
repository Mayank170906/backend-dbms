# Backend DBMS — Documentation Site

A static, dependency-free documentation portal for the Backend DBMS project:
plain HTML, CSS, and vanilla JS — no build step, no framework, works opened
directly from disk (`file://`) or served by any static host.

## Structure

The site is organized into 13 top-level sections, each its own folder, plus
the homepage at `index.html`:

| Folder | Section |
|---|---|
| `overview/` | What the project is, features, current implementation status, tech stack |
| `getting-started/` | Prerequisites, install, env setup, running locally/with Docker |
| `requirements/` | SRS, functional/non-functional requirements, actors, use cases, traceability |
| `architecture/` | System architecture, HLD/LLD, request lifecycle, auth flow, OOP design |
| `codebase/` | Project structure, apps, models, views, serializers, URLs, services, signals, config |
| `api/` | API overview, auth, endpoints, request/response examples, errors |
| `database/` | ER diagram, models, relationships, constraints, indexes, migrations |
| `workflows/` | User/business workflows and sequence diagrams |
| `testing/` | Test architecture, test cases, running tests, coverage |
| `deployment/` | Local, Docker, Render, Supabase, env vars, production config, troubleshooting |
| `developer-notes/` | Django/DRF/ORM/auth/deployment concepts, taught with real project code |
| `reference/` | Env var table, commands, glossary, ADRs, FAQ |
| `legal/` | License, terms, attribution |

## How navigation and search work

There is no per-page hand-written sidebar. `assets/js/nav-data.js` is the
single source of truth for the whole site's page tree (13 sections × their
pages); `assets/js/main.js` renders the sidebar, breadcrumb, and prev/next
footer links from it at runtime, using two globals every page declares in a
small inline `<script>` right after `<meta charset>`:

```html
<script>window.DOCS_BASE = "../"; window.DOCS_PAGE = "overview/features.html";</script>
```

(`DOCS_BASE` is `""` only for `index.html`; every other page is one folder
deep, so it's `"../"`.)

`assets/js/search-index.js` is a hand-maintained array — one entry per page,
with real model/class/endpoint/env-var names in its `keywords` — that powers
the `Ctrl+K` / `/` search palette.

**Adding a new page** means three edits: the new `.html` file (copy an
existing page's `<head>`/sidebar/search-overlay boilerplate), a new entry in
`nav-data.js`, and a new entry in `search-index.js`. Skipping either data
file means the page exists but is unreachable from the nav or search.

## Theme

Dark/light follows the OS by default (`prefers-color-scheme`). The toggle
button in the sidebar header lets a visitor override that explicitly; the
choice is stored in `localStorage` and applied via `data-theme="light"` /
`data-theme="dark"` on `<html>`.

## Viewing locally

Just open `index.html` in a browser. Or, for a local server:

```bash
cd tutorials
python -m http.server 8080
# then open http://localhost:8080
```

## Deploying to GitHub Pages

A workflow at `.github/workflows/deploy-tutorials.yml` deploys this exact
folder automatically on every push to `main`/`master` that touches
`tutorials/`, using GitHub's Actions-based Pages deployment
(`actions/deploy-pages`). It needs no changes for this site's folder
structure — it uploads the whole `tutorials/` directory as-is.

One-time setup: in the repo's **Settings → Pages**, set **Source** to
**"GitHub Actions"** (not a branch). After that, every push does the rest.

To trigger a deploy manually without a push, use the workflow's "Run
workflow" button under the **Actions** tab (`workflow_dispatch`).
