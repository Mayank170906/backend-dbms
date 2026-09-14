// Single source of truth for the documentation's navigation tree: the
// sidebar, breadcrumbs, and prev/next footer links are all rendered from
// this one structure by main.js. Every page declares which entry it is via
// `window.DOCS_PAGE` (see the inline script at the top of each page's
// <body>) rather than main.js trying to infer it from location.pathname —
// that keeps this working identically under file://, GitHub Pages project
// paths, and any other host.
const NAV_SECTIONS = [
  {
    title: "Overview",
    pages: [
      { title: "Hub", href: "index.html" },
      { title: "Project Overview", href: "overview/project-overview.html" },
      { title: "Features", href: "overview/features.html" },
      { title: "Current Status", href: "overview/current-status.html" },
      { title: "Technology Stack", href: "overview/technology-stack.html" },
      { title: "System Overview", href: "overview/system-overview.html" },
    ],
  },
  {
    title: "Getting Started",
    pages: [
      { title: "Prerequisites", href: "getting-started/prerequisites.html" },
      { title: "Installation", href: "getting-started/installation.html" },
      { title: "Environment Setup", href: "getting-started/environment-setup.html" },
      { title: "Database Setup", href: "getting-started/database-setup.html" },
      { title: "Running Locally", href: "getting-started/running-locally.html" },
      { title: "Running with Docker", href: "getting-started/running-with-docker.html" },
      { title: "First Request", href: "getting-started/first-request.html" },
    ],
  },
  {
    title: "Requirements",
    pages: [
      { title: "SRS", href: "requirements/srs.html" },
      { title: "Functional Requirements", href: "requirements/functional-requirements.html" },
      { title: "Non-Functional Requirements", href: "requirements/non-functional-requirements.html" },
      { title: "Actors", href: "requirements/actors.html" },
      { title: "Use Cases", href: "requirements/use-cases.html" },
      { title: "Traceability Matrix", href: "requirements/traceability-matrix.html" },
    ],
  },
  {
    title: "Architecture",
    pages: [
      { title: "System Architecture", href: "architecture/system-architecture.html" },
      { title: "High-Level Design", href: "architecture/hld.html" },
      { title: "Low-Level Design", href: "architecture/lld.html" },
      { title: "Components", href: "architecture/components.html" },
      { title: "Data Flow", href: "architecture/data-flow.html" },
      { title: "Request Lifecycle", href: "architecture/request-lifecycle.html" },
      { title: "Authentication Flow", href: "architecture/authentication-flow.html" },
      { title: "Deployment Architecture", href: "architecture/deployment-architecture.html" },
      { title: "OOP / Class Design", href: "architecture/oop-class-design.html" },
    ],
  },
  {
    title: "Codebase",
    pages: [
      { title: "Project Structure", href: "codebase/project-structure.html" },
      { title: "Applications", href: "codebase/applications.html" },
      { title: "Models", href: "codebase/models.html" },
      { title: "Views", href: "codebase/views.html" },
      { title: "Serializers", href: "codebase/serializers.html" },
      { title: "URLs", href: "codebase/urls.html" },
      { title: "Services", href: "codebase/services.html" },
      { title: "Permissions", href: "codebase/permissions.html" },
      { title: "Middleware", href: "codebase/middleware.html" },
      { title: "Utilities", href: "codebase/utilities.html" },
      { title: "Signals", href: "codebase/signals.html" },
      { title: "Configuration", href: "codebase/configuration.html" },
    ],
  },
  {
    title: "API",
    pages: [
      { title: "API Overview", href: "api/overview.html" },
      { title: "Authentication", href: "api/authentication.html" },
      { title: "Endpoints", href: "api/endpoints.html" },
      { title: "Request/Response Examples", href: "api/request-response-examples.html" },
      { title: "Error Handling", href: "api/error-handling.html" },
      { title: "API Architecture", href: "api/architecture.html" },
    ],
  },
  {
    title: "Database",
    pages: [
      { title: "Database Overview", href: "database/overview.html" },
      { title: "ER Diagram", href: "database/er-diagram.html" },
      { title: "Models", href: "database/models.html" },
      { title: "Relationships", href: "database/relationships.html" },
      { title: "Constraints", href: "database/constraints.html" },
      { title: "Indexes", href: "database/indexes.html" },
      { title: "Migrations", href: "database/migrations.html" },
    ],
  },
  {
    title: "Workflows",
    pages: [
      { title: "User Workflows", href: "workflows/user-workflows.html" },
      { title: "Authentication Workflow", href: "workflows/authentication-workflow.html" },
      { title: "API Request Workflow", href: "workflows/api-request-workflow.html" },
      { title: "Major Business Workflows", href: "workflows/major-business-workflows.html" },
      { title: "Sequence Diagrams", href: "workflows/sequence-diagrams.html" },
    ],
  },
  {
    title: "Testing",
    pages: [
      { title: "Test Architecture", href: "testing/architecture.html" },
      { title: "Test Cases", href: "testing/test-cases.html" },
      { title: "Running Tests", href: "testing/running-tests.html" },
      { title: "Coverage", href: "testing/coverage.html" },
    ],
  },
  {
    title: "Deployment",
    pages: [
      { title: "Local", href: "deployment/local.html" },
      { title: "Docker", href: "deployment/docker.html" },
      { title: "Render", href: "deployment/render.html" },
      { title: "Supabase", href: "deployment/supabase.html" },
      { title: "Environment Variables", href: "deployment/environment-variables.html" },
      { title: "Production Configuration", href: "deployment/production-configuration.html" },
      { title: "Troubleshooting", href: "deployment/troubleshooting.html" },
    ],
  },
  {
    title: "Developer Notes",
    pages: [
      { title: "Django Concepts", href: "developer-notes/django-concepts.html" },
      { title: "DRF Concepts", href: "developer-notes/drf-concepts.html" },
      { title: "ORM Notes", href: "developer-notes/orm-notes.html" },
      { title: "Authentication Notes", href: "developer-notes/authentication-notes.html" },
      { title: "Deployment Notes", href: "developer-notes/deployment-notes.html" },
      { title: "What Does This Code Mean?", href: "developer-notes/what-does-this-code-mean.html" },
    ],
  },
  {
    title: "Reference",
    pages: [
      { title: "Environment Variables", href: "reference/environment-variables.html" },
      { title: "Commands", href: "reference/commands.html" },
      { title: "Configuration", href: "reference/configuration.html" },
      { title: "Glossary", href: "reference/glossary.html" },
      { title: "ADRs", href: "reference/adrs.html" },
      { title: "FAQ", href: "reference/faq.html" },
    ],
  },
  {
    title: "Legal",
    pages: [
      { title: "License", href: "legal/license.html" },
      { title: "Terms", href: "legal/terms.html" },
      { title: "Attribution", href: "legal/attribution.html" },
    ],
  },
];

// Flat ordering used for prev/next footer navigation.
const NAV_FLAT = NAV_SECTIONS.flatMap((section) =>
  section.pages.map((page) => ({ ...page, section: section.title }))
);
