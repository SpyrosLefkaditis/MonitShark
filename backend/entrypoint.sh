#!/bin/sh
set -eu

mkdir -p "${DATA_DIR:-/data}"
mkdir -p "${CONFIG_DIR:-/config}"

# Bootstrap config/ from config.example/ if missing.
CFG="${CONFIG_DIR:-/config}"
EX="${CONFIG_EXAMPLE_DIR:-/config.example}"
if [ -d "$EX" ]; then
    [ -f "$CFG/port.yml"  ] || cp "$EX/port.yml"  "$CFG/port.yml"
    [ -f "$CFG/users.yml" ] || cp "$EX/users.yml" "$CFG/users.yml"
fi

# Bootstrap users (generates pwd if any user has empty hash, prints once).
python -c "
from app.auth import bootstrap_users
msg = bootstrap_users()
if msg:
    print(msg, flush=True)
"

# Honor config/port.yml backend.bind_port (overrides env BIND_PORT if set).
PORT_OVERRIDE=$(python -c "
from app.config import load_port_config
cfg = load_port_config()
print(cfg.bind_port)
" 2>/dev/null || echo "")

if [ -n "$PORT_OVERRIDE" ]; then
    BIND_PORT="$PORT_OVERRIDE"
fi

exec uvicorn app.main:app \
    --host "${BIND_HOST:-127.0.0.1}" \
    --port "${BIND_PORT:-8000}" \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
