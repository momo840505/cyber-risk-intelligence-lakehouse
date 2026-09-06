#!/bin/sh
set -e

# docker-compose bind-mounts the host's ./monitoring directory over
# /app/monitoring at container start, so it arrives owned by whoever
# owns it on the host, not by the "appuser" account created at build
# time. Fix that here (as root, before dropping privileges) so the API
# can still write monitoring/api_usage_log.csv. analytics/ and models/
# are mounted read-only and are world-readable by default, so they
# don't need this.
chown -R appuser:appuser /app/monitoring 2>/dev/null || true

exec su appuser -s /bin/sh -c 'exec "$0" "$@"' -- "$@"
