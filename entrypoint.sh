#!/bin/sh
set -eu

mkdir -p /app/analytics /app/models /app/monitoring /app/reports
chown -R appuser:appuser /app/monitoring /app/reports 2>/dev/null || true

if [ -n "${ARTIFACT_BUCKET:-}" ]; then
    python -m api.bootstrap_artifacts
fi

exec su appuser -s /bin/sh -c 'exec "$0" "$@"' -- "$@"
