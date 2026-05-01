#!/bin/sh
set -eu

mkdir -p "${DATA_DIR:-/data}"

exec uvicorn app.main:app \
    --host "${BIND_HOST:-127.0.0.1}" \
    --port "${BIND_PORT:-8000}" \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
