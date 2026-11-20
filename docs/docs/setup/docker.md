---
icon: lucide/container
---

# Docker

Three Compose files at the repo root, meant to be combined, not used
alone:

- `compose.yaml` — base: a `backend` (gunicorn) and `frontend` (nginx,
  serving the production build, reverse-proxying `/api/` to `backend`)
  service. No published ports, no dev tooling.
- `compose.dev.yaml` — dev overlay: Flask debug server + Vite dev server,
  ports published to `localhost`, `develop.watch` syncs source edits live.
- `compose.prod.yaml` — prod overlay: `restart: unless-stopped`, publishes
  `frontend` on `127.0.0.1:8080`.

Build context is the repo root for both services, so run these commands
from there, not from `backend/`/`frontend/`.

## Prerequisites

Same as [Running in production](production.md)'s Step 1, Docker or not:

```bash
cp backend/.env.example backend/.env
python3 -c "import secrets; print(secrets.token_hex(32))"   # -> .env's SECRET_KEY=
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"   # -> .env's CNA_CREDENTIAL_ENCRYPTION_KEY= (a valid Fernet key)
```

`config/vulniverse.toml` is optional — no file falls back to the committed
`config/vulniverse.toml.sample`'s defaults, a valid state, not an error.

## Development

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build --watch
```

Backend: `http://127.0.0.1:5000`. Frontend (Vite, with HMR):
`http://127.0.0.1:5173`.


## Production

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

Runs the real gunicorn/nginx build, published on `127.0.0.1:8080` — put
your own TLS termination (Caddy, nginx, Traefik) in front of it.

## First run

`backend_instance` is a plain named volume, named after the Compose
project (by default the repo directory), not the overlay. Dev and prod
started from the same checkout therefore share one database; use
`docker compose -p <name>` to keep them apart. The volume is empty the
first time a project starts. Migrate the DB and for a local only setup
create the local user:

```bash
docker compose exec backend flask --app vulniverse_api db upgrade
docker compose exec backend flask --app vulniverse_api init-local-user
```

In `multiuser` mode, skip `init-local-user` and create the first admin
instead (see [Configuration](config.md)):

```bash
docker compose exec backend flask --app vulniverse_api create-admin admin@example.com
```

