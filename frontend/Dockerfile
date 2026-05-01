# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first for better layer caching. Use `npm ci` if a lockfile is
# present, otherwise fall back to `npm install` (the lockfile is generated on
# the first install and committed thereafter).
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then \
        npm ci --no-audit --no-fund ; \
    else \
        npm install --no-audit --no-fund ; \
    fi

COPY . .
RUN npm run build

# ---------- artifact-only stage ----------
# Tiny image whose only job is to hold /app/dist so the compose `command:` can
# copy it into the shared `frontend_dist` volume that Caddy serves from.
FROM alpine:3.20
RUN apk add --no-cache coreutils
WORKDIR /app
COPY --from=builder /app/dist /app/dist
CMD ["sh", "-c", "echo 'frontend artifact ready at /app/dist'"]
