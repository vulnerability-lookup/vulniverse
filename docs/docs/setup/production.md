---
icon: lucide/server
---

# Running in production

The commands in [Build from source](../development/from-source.md) (`flask --app vulniverse_api run
--debug`, `npm run dev`) are development-only. Follow these steps in order
for a real, bare-metal deployment (systemd + nginx on the host). If you'd
rather run it in containers instead, see [Docker](docker.md).

## Step 1 — Configure the environment

`create_app()` requires a `SECRET_KEY` and a `CNA_CREDENTIAL_ENCRYPTION_KEY`
from the environment — it refuses to start without either.

1. Install the dependencies and copy the template:
   ```bash
   cd backend
   uv sync --no-dev
   cp .env.example .env
   ```
   This creates `backend/.venv`, which the systemd unit in
   [Step 5](#step-5-supervise-it-with-systemd) runs from. The unit
   assumes the checkout lives at `/opt/vulniverse`; adjust its paths if
   yours is elsewhere.
2. Generate a real secret and paste it into `.env`'s `SECRET_KEY=`:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Generate a Fernet key and paste it into `.env`'s
   `CNA_CREDENTIAL_ENCRYPTION_KEY=` — this encrypts each user's CNA
   credentials at rest. Changing it later makes previously-saved
   credentials undecryptable, so treat it like `SECRET_KEY`: generate it
   once, keep it, back it up:
   ```bash
   uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Leave `DATABASE_URL` unset for now if you're staying on SQLite — skip to
   [Step 3](#step-3-run-migrations). Otherwise continue to Step 2.


## Step 2 — (Optional) Set up PostgreSQL

Skip this entirely unless you want to run a separate PostgreSQL instance.

1. Create a dedicated role and database — don't reuse one that belongs to
   another application:
   ```bash
   sudo -u postgres psql -c "CREATE USER vulniverse WITH PASSWORD 'choose-a-real-password';"
   sudo -u postgres psql -c "CREATE DATABASE vulniverse OWNER vulniverse;"
   ```
2. Set `DATABASE_URL` in `.env`, using the `+psycopg` scheme — plain
   `postgresql://` resolves to the older `psycopg2` driver, which isn't
   installed here (`psycopg[binary]` is):
   ```
   DATABASE_URL=postgresql+psycopg://vulniverse:choose-a-real-password@localhost:5432/vulniverse
   ```
3. Continue to Step 3 — migrations run exactly the same way regardless of
   which database you're on.

## Step 3 — Run migrations

Run the DB migrations:

```bash
cd backend
uv run flask --app vulniverse_api db upgrade
```

If you're running in local mode (`[server] mode = "local"` in
`config/vulniverse.toml`, the default), also create the internal local
user — this is a separate, one-time step migrations don't do for you:

```bash
uv run flask --app vulniverse_api init-local-user
```

Without it, every request gets "Authentication required" instead of
being auto-authenticated, even though the deployment is genuinely in
local mode — `db upgrade` only creates the `user` table, not this row.

## Step 4 — Run under gunicorn

`flask run --debug` is the development server — with `debug=True` it
exposes Werkzeug's interactive debugger, which allows arbitrary code
execution to anyone who can trigger an unhandled exception. Never run it
outside development.

1. Start the app using gunicorn:
   ```bash
   uv run gunicorn --worker-class gthread --workers 2 --threads 8 --bind 127.0.0.1:8000 wsgi:app
   ```
   Two workers is deliberate, not a placeholder: SQLite allows only one
   writer at a time, so more worker *processes* sharing the one SQLite
   file risks lock contention under real concurrent writes. 

2. Confirm it's actually answering:
   ```bash
   curl http://127.0.0.1:8000/api/v1/health
   ```

## Step 5 — Supervise it with systemd

`backend/deploy/vulniverse.service` is a template to run the backend as a systemd service. Copy
it to your systemd path and adjust the values:

```bash
sudo cp backend/deploy/vulniverse.service /etc/systemd/system/vulniverse.service
```

To use it follow these steps:

1. **Remove or fill in the placeholder keys.** The template sets
   `Environment=SECRET_KEY=replace-…` and
   `Environment=CNA_CREDENTIAL_ENCRYPTION_KEY=replace-…`. Values already
   in the environment win over `backend/.env`, so these placeholders
   would be used instead of your real keys — and an invalid Fernet key
   breaks CNA credentials and 2FA. Delete both lines so `.env` is used,
   or replace them with your real values.
2. **Create the service user** the template runs as (or edit `User=`/
   `Group=` to an existing one):
   ```bash
   sudo useradd --system --no-create-home vulniverse
   ```
3. **Install and start it**. The unit runs `db upgrade` (`ExecStartPre=`)
   before every start, so migrations stay current after updates:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now vulniverse
   systemctl status vulniverse
   ```

## Step 6 — Serve the frontend and expose it with nginx

1. Build the frontend:
   ```bash
   cd frontend
   npm ci
   npm run build
   ```
   This writes static files to `frontend/dist`.
2. `backend/deploy/vulniverse.nginx.conf` is a template that serves
   `frontend/dist` and reverse-proxies `/api/` to gunicorn. Copy it and
   adjust `server_name` and the `root` path for your deployment:
   ```bash
   sudo cp backend/deploy/vulniverse.nginx.conf /etc/nginx/sites-available/vulniverse
   sudo ln -s /etc/nginx/sites-available/vulniverse /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```
3. Add TLS (for example with Certbot/Let's Encrypt) rather than serving
   over plain HTTP in production.

