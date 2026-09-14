#!/bin/sh
set -e

# docker-compose's `depends_on: condition: service_healthy` already waits for
# Postgres to accept TCP connections, but "accepting connections" and "ready
# to authenticate" aren't always the same instant, so double-check here too
# before every container command (web, celery worker, celery beat) touches
# the database.
if [ -n "$POSTGRES_HOST" ] || [ -n "$DATABASE_URL" ]; then
  python - <<'PYEOF'
import os
import sys
import time

import dj_database_url
import psycopg

config = dj_database_url.config(default=os.environ.get("DATABASE_URL", ""))
if not config:
    sys.exit(0)

for attempt in range(30):
    try:
        psycopg.connect(
            dbname=config["NAME"],
            user=config["USER"],
            password=config["PASSWORD"],
            host=config["HOST"],
            port=config["PORT"],
            connect_timeout=2,
        ).close()
        break
    except psycopg.OperationalError:
        time.sleep(1)
else:
    sys.exit("Postgres did not become available in time")
PYEOF
fi

exec "$@"
