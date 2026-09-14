# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Fail fast on unhandled exceptions instead of buffering stdout, and skip
# .pyc write-back on a container filesystem that gets thrown away anyway.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# libpq is needed at runtime by psycopg (even the "binary" wheel variant
# links against it); build-essential is only needed transiently to build any
# dependency without a prebuilt wheel, so it's removed in the same layer.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies before copying the rest of the source so this layer
# is cached across builds unless pyproject.toml/uv.lock actually change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && uv sync --frozen --no-install-project --no-dev \
    && apt-get purge -y build-essential libpq-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x docker/entrypoint.sh

# Static assets are content-hashed by ManifestStaticFilesStorage, not by
# SECRET_KEY or the database — collectstatic can run at build time against
# throwaway placeholders that are never used at runtime. production.py
# deliberately raises if SECRET_KEY/ALLOWED_HOSTS/DATABASE_URL are unset
# (Phase 1), so this step needs *some* values to get past those checks; the
# real ones come from the container's actual environment when it runs.
RUN SECRET_KEY=build-time-placeholder-unused-at-runtime \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://build:build@localhost/build \
    python manage.py collectstatic --noinput --settings=config.settings.production

# Runs as a non-root user in every environment (dev included) rather than
# only hardening the production image — one Dockerfile, one behavior to
# reason about. /app is bind-mounted over in docker-compose.yml for local
# dev, so ownership of the image's copy barely matters there; it matters
# for docker-compose.prod.yml, which ships this image's files as-is.
# mkdir'd explicitly (not left for Django to create on first save) so it
# exists, with the right ownership, at build time: Docker initializes a
# fresh named volume by copying whatever the image already has at that
# path (docker-compose.yml mounts one at /app/media) — if the directory
# didn't exist yet, that copy would have nothing to seed the volume's
# ownership from.
RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /app/media \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
