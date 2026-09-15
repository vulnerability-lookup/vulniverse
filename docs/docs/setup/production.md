---
icon: lucide/server
---

# Running in production

The commands in [Get started](setup.md) (`flask --app vulniverse_api run
--debug`, `npm run dev`) are development-only. Follow these steps in order
for a real deployment.

## Step 1 — Configure the environment

`create_app()` requires a `SECRET_KEY` and a `CNA_CREDENTIAL_ENCRYPTION_KEY`
from the environment — it refuses to start without either.

1. Copy the template:
   ```bash
   cd backend
   cp .env.example .env
   ```
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
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
4. Leave `DATABASE_URL` unset for now if you're staying on SQLite — skip to
   [Step 3](#step-3-run-migrations). Otherwise continue to Step 2.


## Step 2 — (Optional) Set up PostgreSQL

Skip this entirely unless you want to run a seperate PostgreSQL instance.

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

## Step 4 — Run under gunicorn

`flask run --debug` is the development server — with `debug=True` it
exposes Werkzeug's interactive debugger, which allows arbitrary code
execution to anyone who can trigger an unhandled exception. Never run it
outside development.

1. Start the app using gunicorn:
   ```bash
   uv run gunicorn --workers 2 --bind 127.0.0.1:8000 wsgi:app
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
it to your sytemd path and adjust the values:

```bash
sudo cp backend/deploy/vulniverse.service /etc/systemd/system/vulniverse.service
```

To use it follow these steps:

1. **Create the service user** the template runs as (or edit `User=`/
   `Group=` to an existing one):
   ```bash
   sudo useradd --system --no-create-home vulniverse
   ```
2. **Install and start it**:
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
3. Add TLS with rather than serving over plain HTTP in production.

