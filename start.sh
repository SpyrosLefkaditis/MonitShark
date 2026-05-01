#!/bin/sh
# MonitShark — one-command bootstrap + run.
#   ./start.sh           build + up -d
#   ./start.sh logs      tail backend logs
#   ./start.sh down      stop everything
#   ./start.sh ps        status
set -eu

# 1) Bootstrap .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    JWT=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 32 2>/dev/null || true)
    if [ -n "${JWT:-}" ]; then
        sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=${JWT}|" .env && rm -f .env.bak
    fi
    echo
    echo "  .env created. Edit it to set GROQ_API_KEY (https://console.groq.com)."
    echo "  Then re-run: ./start.sh"
    echo
    exit 0
fi

# 2) Bootstrap config/ from config.example/ if missing
mkdir -p config
[ -f config/port.yml  ] || cp config.example/port.yml  config/port.yml  2>/dev/null || true
[ -f config/users.yml ] || cp config.example/users.yml config/users.yml 2>/dev/null || true

# 3) Read ports from config/port.yml into env (no yq required)
if [ -f config/port.yml ]; then
    HTTPS=$(awk '/^[[:space:]]*https:/ {print $2; exit}' config/port.yml | tr -d ' "')
    HTTP=$(awk  '/^[[:space:]]*http:/  {print $2; exit}' config/port.yml | tr -d ' "')
    [ -n "${HTTPS:-}" ] && export HTTPS_PORT="$HTTPS"
    [ -n "${HTTP:-}"  ] && export HTTP_PORT="$HTTP"
fi

# 4) Dispatch
case "${1:-up}" in
    up)
        exec docker compose up -d --build
        ;;
    logs)
        exec docker compose logs -f --tail=200 backend
        ;;
    down)
        exec docker compose down
        ;;
    ps)
        exec docker compose ps
        ;;
    *)
        exec docker compose "$@"
        ;;
esac
